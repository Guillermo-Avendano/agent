"""
ContentEdge MCP Server — exposes Content Repository operations as MCP tools.

Tools:
  - list_content_classes: List available content classes (getRecordTypes)
  - list_indexes: List indexes and index groups (with mandatory grouping info)
  - search_documents: Search documents by index values
  - archive_documents: Archive files (PDF, TXT, JPG, PNG) with metadata
  - retrieve_document: Get a viewer URL for a document by objectId
  - get_versions: Get document versions for a report within a date range
  - smart_chat: Ask questions to the Smart Chat AI (repository-wide or scoped to documents)
"""

import os
import json
import logging
import time
import yaml
from copy import deepcopy

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("contentedge-mcp")

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------
CONF_DIR = os.path.join(os.path.dirname(__file__), "conf")
WORK_DIR = os.environ.get("CE_WORK_DIR", os.path.join(os.path.dirname(__file__), "files"))

SOURCE_YAML = os.path.join(CONF_DIR, "repository_source.yaml")


def _patch_yaml_from_env(yaml_path: str, prefix: str) -> None:
    """Overwrite YAML connection params from environment variables at startup.

    Env vars mapping (prefix = CE_SOURCE_ or CE_TARGET_):
      {prefix}REPO_URL          -> repository.repo_url
      {prefix}REPO_NAME         -> repository.repo_name
      {prefix}REPO_USER         -> repository.repo_user
      {prefix}REPO_PASS         -> repository.repo_pass
      {prefix}REPO_SERVER_USER  -> repository.repo_server_user
      {prefix}REPO_SERVER_PASS  -> repository.repo_server_pass
    """
    env_map = {
        "REPO_URL": "repo_url",
        "REPO_NAME": "repo_name",
        "REPO_USER": "repo_user",
        "REPO_PASS": "repo_pass",
        "REPO_SERVER_USER": "repo_server_user",
        "REPO_SERVER_PASS": "repo_server_pass",
    }

    updates: dict[str, str] = {}
    for env_suffix, yaml_key in env_map.items():
        val = os.environ.get(f"{prefix}{env_suffix}", "")
        if val:  # skip empty / unset
            updates[yaml_key] = val

    if not updates:
        return

    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f) or {}

    repo = config.setdefault("repository", {})
    repo.update(updates)

    with open(yaml_path, "w") as f:
        yaml.dump(config, f, sort_keys=False)

    logger.info("Patched %s with env overrides: %s", yaml_path, list(updates.keys()))


def _init_configs():
    """Patch source YAML from env vars, then build ContentConfig object."""
    _patch_yaml_from_env(SOURCE_YAML, "CE_SOURCE_")

    # Import ContentConfig after patching so __init__ reads final values
    from lib.content_config import ContentConfig

    source_cfg = ContentConfig(SOURCE_YAML)
    logger.info("Source repository: %s @ %s", source_cfg.repo_name, source_cfg.base_url)

    return source_cfg


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------
source_config = _init_configs()

mcp = FastMCP("ContentEdge")


# ---------------------------------------------------------------------------
# Repository health check
# ---------------------------------------------------------------------------
def _check_repository_active(config) -> str | None:
    """Verify the Content Repository is active by calling /repositories.

    Returns None if the repository is active, or a JSON error string
    if the repository is unreachable or unavailable.
    """
    try:
        url = f"{config.repo_url}/repositories"
        headers = {"Authorization": f"Basic {config.encoded_credentials}"}
        resp = requests.get(url, headers=headers, verify=False, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items", [])
        for item in items:
            if item.get("name") == config.repo_name:
                return None  # Repository is active

        # Repository name not found in the list
        return json.dumps({
            "error": f"Repository '{config.repo_name}' not found. "
                     "Please verify the repository is created and active in ContentEdge."
        })

    except requests.exceptions.ConnectionError:
        return json.dumps({
            "error": f"Cannot connect to Content Repository at {config.base_url}. "
                     "The server appears to be down. Please start the Content Repository and try again."
        })
    except requests.exceptions.Timeout:
        return json.dumps({
            "error": f"Connection to Content Repository at {config.base_url} timed out. "
                     "The server may be overloaded or unreachable. Please try again later."
        })
    except requests.exceptions.HTTPError as exc:
        return json.dumps({
            "error": f"Content Repository returned HTTP {exc.response.status_code}. "
                     "The repository may not be active. Please activate the repository and try again."
        })
    except Exception as exc:
        return json.dumps({
            "error": f"Failed to verify Content Repository status: {exc}. "
                     "Please ensure the repository is running and accessible."
        })

# ---------------------------------------------------------------------------
# MCP Tool: list_content_classes
# ---------------------------------------------------------------------------
@mcp.tool()
def list_content_classes() -> str:
    """List all available Content Classes in the repository.

    Returns the id, name and description of every Content Class.
    Use the id as the *content_class* parameter when archiving documents.

    Returns:
        JSON array with objects containing id, name, and description.
    """
    headers = deepcopy(source_config.headers)
    headers["Accept"] = (
        "application/vnd.asg-mobius-admin-reports.v3+json,"
        "application/vnd.asg-mobius-admin-reports.v2+json,"
        "application/vnd.asg-mobius-admin-reports.v1+json"
    )

    repo_err = _check_repository_active(source_config)
    if repo_err:
        return repo_err

    tm = str(int(time.time() * 1000))
    url = f"{source_config.repo_admin_url}/reports?limit=200&reportid=*&timestamp={tm}"
    logger.info("list_content_classes → GET %s", url)

    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.error("list_content_classes failed: %s", exc)
        return json.dumps({"error": str(exc)})

    items = data.get("items", [])
    result = [
        {
            "id": it.get("id", ""),
            "name": it.get("name", ""),
            "description": it.get("details", ""),
        }
        for it in items
    ]
    logger.info("Found %d content class(es).", len(result))
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# MCP Tool: list_indexes
# ---------------------------------------------------------------------------
@mcp.tool()
def list_indexes() -> str:
    """List all available indexes and index groups in the repository.

    Returns two sections:
    - **index_groups**: Groups of indexes that MUST ALL be provided together
      when archiving a document.  Every index in a group is mandatory.
    - **individual_indexes**: Standalone indexes that can be used independently.

    Use the index ids as metadata key names when archiving documents.

    Returns:
        JSON object with "index_groups" and "individual_indexes" (only indexes not in any group).
    """
    tm = str(int(time.time() * 1000))

    repo_err = _check_repository_active(source_config)
    if repo_err:
        return repo_err

    # 1) Fetch index groups (topicgroups)
    hg = deepcopy(source_config.headers)
    hg["Accept"] = "application/vnd.asg-mobius-admin-topic-groups.v1+json"
    groups_url = f"{source_config.repo_admin_url}/topicgroups?limit=200&groupid=*&timestamp={tm}"

    try:
        rg = requests.get(groups_url, headers=hg, verify=False, timeout=30)
        rg.raise_for_status()
        groups_data = rg.json().get("items", [])
    except Exception as exc:
        logger.error("list_indexes (groups) failed: %s", exc)
        return json.dumps({"error": str(exc)})

    # Collect all index ids that belong to a group
    grouped_ids: set[str] = set()
    index_groups = []
    for g in groups_data:
        topics = [
            {
                "id": t.get("id", ""),
                "name": t.get("name", ""),
                "dataType": t.get("dataType", "Character"),
            }
            for t in g.get("topics", [])
        ]
        for t in topics:
            grouped_ids.add(t["id"])
        index_groups.append({
            "group_id": g.get("id", ""),
            "group_name": g.get("name", ""),
            "mandatory_note": "ALL indexes in this group must be provided when archiving.",
            "indexes": topics,
        })

    # 2) Fetch individual indexes (topics)
    ht = deepcopy(source_config.headers)
    ht["Accept"] = "application/vnd.asg-mobius-admin-topics.v1+json"
    topics_url = f"{source_config.repo_admin_url}/topics?limit=200&topicid=*&timestamp={tm}"

    try:
        rt = requests.get(topics_url, headers=ht, verify=False, timeout=30)
        rt.raise_for_status()
        topics_data = rt.json().get("items", [])
    except Exception as exc:
        logger.error("list_indexes (topics) failed: %s", exc)
        return json.dumps({"error": str(exc)})

    individual = [
        {
            "id": it.get("id", ""),
            "name": it.get("name", ""),
            "description": it.get("details", ""),
            "dataType": it.get("dataType", "Character"),
        }
        for it in topics_data
        if it.get("id", "") not in grouped_ids
    ]

    logger.info("Found %d index group(s), %d individual index(es).",
                len(index_groups), len(individual))

    return json.dumps({
        "index_groups": index_groups,
        "individual_indexes": individual,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# MCP Tool: search_documents
# ---------------------------------------------------------------------------
@mcp.tool()
def search_documents(
    constraints: list[dict[str, str]],
    conjunction: str = "AND",
) -> str:
    """Search for documents in the repository by index values.

    Args:
        constraints: List of search constraints. Each constraint is a dict with:
            - index_name: Name of the index to search (e.g. "DEPT", "CUST_ID").
            - operator: Comparison operator. One of: EQ, NE, LT, LE, GT, GE, LK, BT, NB, NU, NN.
                        Defaults to "EQ" if omitted.
            - value: The value to search for.
        conjunction: How to combine multiple constraints — "AND" or "OR". Default "AND".

    Returns:
        JSON with the list of matching document objectIds.

    Example constraints:
        [{"index_name": "DEPT", "operator": "EQ", "value": "0099"}]
    """
    from lib.content_search import IndexSearch, ContentSearch

    repo_err = _check_repository_active(source_config)
    if repo_err:
        return repo_err

    try:
        search = IndexSearch(conjunction=conjunction)
        for c in constraints:
            idx = c.get("index_name", "")
            op = c.get("operator", "EQ")
            val = c.get("value", "")
            if not idx:
                return json.dumps({"error": "Each constraint must have 'index_name'."})
            search.add_constraint(index_name=idx, operator=op, index_value=val)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    searcher = ContentSearch(source_config)
    object_ids = searcher.search_index(search)

    logger.info("search_documents: %d result(s) for %s", len(object_ids), constraints)
    return json.dumps({"count": len(object_ids), "object_ids": object_ids})


# ---------------------------------------------------------------------------
# MCP Tool: archive_documents
# ---------------------------------------------------------------------------
@mcp.tool()
def archive_documents(
    content_class: str,
    files: list[str],
    metadata: dict[str, str],
    sections: list[str] | None = None,
) -> str:
    """Archive one or more documents into the Content Repository.

    Each file is archived under the given content class with the supplied
    index metadata.  Supported file types: PDF, TXT, JPG, PNG.

    Args:
        content_class: Content class name in the repository (e.g. "AC001", "LISTFILE").
        files: List of file paths (relative to the working directory) to archive.
        metadata: Dictionary of index name-value pairs applied to every document
                  (e.g. {"CUST_ID": "3000", "LOAN_ID": "H366100", "REQ_DATE": "2025-07-05"}).
        sections: Optional list of section names, one per file.  If provided it must
                  have the same length as *files*.  Each section is truncated to 20 chars.

    Returns:
        JSON string with the archiving result for each file.
    """
    from lib.content_archive_metadata import (
        ArchiveDocument,
        ArchiveDocumentCollection,
        ContentArchiveMetadata,
    )

    repo_err = _check_repository_active(source_config)
    if repo_err:
        return repo_err

    if sections and len(sections) != len(files):
        return json.dumps({"error": "Length of 'sections' must match length of 'files'."})

    collection = ArchiveDocumentCollection()
    resolved_paths: list[str] = []

    for idx, rel_path in enumerate(files):
        # Resolve relative to working dir
        abs_path = os.path.join(WORK_DIR, rel_path) if not os.path.isabs(rel_path) else rel_path
        abs_path = os.path.normpath(abs_path)

        # Ensure the file is inside the allowed working directory
        if not abs_path.startswith(os.path.normpath(WORK_DIR)):
            return json.dumps({"error": f"File '{rel_path}' is outside the working directory."})

        if not os.path.isfile(abs_path):
            return json.dumps({"error": f"File not found: '{rel_path}'"})

        try:
            doc = ArchiveDocument(content_class, abs_path)
        except ValueError as exc:
            return json.dumps({"error": str(exc)})

        # Section
        if sections:
            doc.set_section(sections[idx])

        # Metadata
        for name, value in metadata.items():
            doc.add_metadata(name, str(value))

        collection.add_document(doc)
        resolved_paths.append(abs_path)

    # Archive via source repository config
    archiver = ContentArchiveMetadata(source_config)
    status_code = archiver.archive_metadata(collection)

    results = []
    for i, doc in enumerate(collection.objects):
        results.append({
            "file": os.path.basename(resolved_paths[i]),
            "content_class": content_class,
            "status": status_code,
        })

    if status_code in (200, 201):
        logger.info("Archived %d document(s) successfully (HTTP %s).", len(files), status_code)
        return json.dumps({"success": True, "archived": results})
    else:
        logger.error("Archive failed with status %s", status_code)
        return json.dumps({"success": False, "status": status_code, "archived": results})


# ---------------------------------------------------------------------------
# MCP Tool: get_versions
# ---------------------------------------------------------------------------
@mcp.tool()
def get_versions(
    report_id: str,
    version_from: str,
    version_to: str,
) -> str:
    """Get document version object-IDs for a report within a date range.

    Args:
        report_id: Report identifier in the repository (e.g. "AC2020").
        version_from: Start date in format yyyymmddHHMMSS (e.g. "20220401000000").
        version_to: End date in format yyyymmddHHMMSS (e.g. "20220801000000").

    Returns:
        JSON string with version keys and their object IDs.
    """
    from lib.content_class_navigator import ContentClassNavigator

    repo_err = _check_repository_active(source_config)
    if repo_err:
        return repo_err

    navigator = ContentClassNavigator(source_config)
    col = navigator.get_versions(report_id, version_from, version_to)

    return json.dumps({"report_id": report_id, "versions": col})


# ---------------------------------------------------------------------------
# MCP Tool: retrieve_document
# ---------------------------------------------------------------------------
@mcp.tool()
def retrieve_document(
    object_id: str,
) -> str:
    """Get a viewer URL for a document from the Content Repository.

    Use search_documents first to obtain objectIds, then call this tool
    to get a URL that opens the document in the Mobius View browser viewer.

    Args:
        object_id: The encrypted objectId returned by search_documents.

    Returns:
        JSON with the viewer URL for the document.
    """
    from lib.content_document import ContentDocument

    repo_err = _check_repository_active(source_config)
    if repo_err:
        return repo_err

    try:
        doc_client = ContentDocument(source_config)
        viewer_url = doc_client.retrieve_document(object_id)
    except ValueError as exc:
        logger.error("retrieve_document failed: %s", exc)
        return json.dumps({"error": str(exc)})
    except Exception as exc:
        logger.error("retrieve_document unexpected error: %s", exc)
        return json.dumps({"error": str(exc)})

    logger.info("Viewer URL obtained for object_id: %s", object_id[:40])

    return json.dumps({
        "success": True,
        "viewer_url": viewer_url,
    })


# ---------------------------------------------------------------------------
# MCP Tool: smart_chat
# ---------------------------------------------------------------------------
@mcp.tool()
def smart_chat(
    question: str,
    document_ids: list[str] | None = None,
    conversation_id: str = "",
) -> str:
    """Ask a question to the Content Repository Smart Chat AI.

    This tool has two modes of operation:

    1. **Repository-wide query** — pass document_ids as an empty list (or
       omit it).  Smart Chat searches the entire repository to answer.
    2. **Scoped to specific documents** — pass a list of objectIds
       (obtained from search_documents) so Smart Chat only analyses those
       documents.

    For follow-up questions in the same conversation, pass the
    conversation_id returned by the previous call to maintain context.

    Typical workflow combining search + smart_chat:
      1. search_documents(constraints=[{"index_name":"CUST_ID","value":"1000"}])
      2. smart_chat(question="Summarize the loan application",
                    document_ids=<object_ids from step 1>)
      3. smart_chat(question="What is the applicant's address?",
                    document_ids=<same ids>,
                    conversation_id=<conversation_id from step 2>)

    Args:
        question: The question to ask Smart Chat.
        document_ids: Optional list of document objectIds to limit scope.
                      Use [] or omit to query the whole repository.
        conversation_id: Optional conversation ID from a previous smart_chat
                         response, to continue the conversation.

    Returns:
        JSON with the answer, conversation_id for follow-ups, and
        matching_document_ids relevant to the answer.
    """
    from lib.content_smart_chat import ContentSmartChat

    repo_err = _check_repository_active(source_config)
    if repo_err:
        return repo_err

    try:
        chat_client = ContentSmartChat(source_config)
        result = chat_client.smart_chat(
            user_query=question,
            document_ids=document_ids,
            conversation=conversation_id,
        )
    except ValueError as exc:
        logger.error("smart_chat failed: %s", exc)
        return json.dumps({"error": str(exc)})
    except Exception as exc:
        logger.error("smart_chat unexpected error: %s", exc)
        return json.dumps({"error": str(exc)})

    logger.info("smart_chat answered (conversation=%s, matching_docs=%d)",
                result.conversation[:20] if result.conversation else "new",
                len(result.object_ids))

    return json.dumps({
        "success": True,
        "answer": result.answer,
        "conversation_id": result.conversation,
        "matching_document_ids": result.object_ids,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8001"))

    logger.info("Starting ContentEdge MCP server (%s) on %s:%s", transport, host, port)

    if transport == "sse":
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
