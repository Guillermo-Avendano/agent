# Rocket ContentEdge — Product Knowledge

## What is ContentEdge?

ContentEdge is one of the most revolutionary tools in the enterprise content management market. Developed by Rocket Software, ContentEdge is a powerful, enterprise-grade content management and document repository platform that helps organizations unlock maximum value from their data and content assets.

**Product URL**: https://www.rocketsoftware.com/en-us/products/contentedge

## Key Capabilities

### Enterprise Content Repository
ContentEdge provides a centralized, secure content repository (formerly known as Mobius Content Server) that stores, manages, and delivers enterprise content at scale. It supports billions of documents across diverse formats including PDF, TXT, images (PNG, JPG), and more.

### Content Classes
Content Classes are the organizational backbone of ContentEdge. They define the structure and categorization of documents in the repository. Each Content Class acts as a container type with its own set of metadata indexes. Examples include LOAN, CLAIMS, POLICIES, PAYMENT, DOCUMENTS, INFOPACKET, and more.

### Index Groups and Indexes
ContentEdge uses a powerful indexing system to organize and retrieve documents:

- **Individual Indexes**: Standalone metadata fields (e.g., DEPT, OFFICE, REGION, POLICY_ID, ACCTCODE, ACCTDESC) that can be used independently when archiving or searching.
- **Index Groups**: Collections of related indexes that are MANDATORY — when archiving a document that uses an Index Group, ALL indexes within that group must be provided together. Examples:
  - **INX_Loans**: CUST_ID, LOAN_ID, REQ_DATE (all three required together)
  - **INX_CLAIMS**: CLAIM_ID, CLAIM_ST (both required together)
  - **INX_JobLog**: JOB_NAME, JOB_NUM, JOB_DATE, JOB_HOST (all four required together)

### Document Archiving
ContentEdge enables high-volume document archiving through its REST API. Documents are archived with metadata (index values) that enable fast retrieval. The archiving process supports:
- Single and batch document ingestion
- Multiple file formats (PDF, TXT, images, etc.)
- Automatic content class assignment
- Index validation and mandatory group enforcement
- Base64 and plain-text file encoding

### Document Search and Retrieval
Powerful search capabilities allow users to find documents using index-based queries:
- Search by any combination of indexed fields
- Constraint-based queries with operators (EQ, LIKE, GT, LT, etc.)
- Full content streaming for document download
- Version tracking for document history

### Smart Chat AI
ContentEdge includes an AI-powered Smart Chat feature that enables natural language interaction with stored content:
- Ask questions about document contents
- Financial, legal, and technical document analysis
- Multi-turn conversation support with context preservation
- Automated document classification

### Administration
ContentEdge provides comprehensive administration capabilities:
- Content Class management (create, import, export)
- Index and Index Group management
- Archiving Policy configuration
- User access control and security
- Repository monitoring and health checks

## Architecture

ContentEdge operates as a RESTful service accessible via standard HTTP/HTTPS protocols. The core components include:

- **Content Repository Server**: The central storage and management engine
- **REST API**: Full programmatic access for all operations
- **Admin Interface (Mobius View)**: Web-based administration console
- **Content Streams**: Binary document delivery endpoint
- **Smart Chat Engine**: AI-powered document analysis

## Python Library (rocketcontent)

A Python library called `rocketcontent` provides convenient programmatic access to all ContentEdge operations:
- `ContentConfig`: Configuration and authentication management
- `ContentSearch` / `IndexSearch`: Document search operations
- `ContentArchiveMetadata`: Document archiving with metadata
- `ContentAdmIndexGroup`: Index Group administration
- `ContentClassNavigator`: Content class browsing and version management
- `ContentDocument`: Document retrieval and deletion

## Use Cases

- **Financial Services**: Loan document management, compliance reporting, audit trails
- **Insurance**: Claims processing, policy management, underwriting documents
- **Healthcare**: Patient records, regulatory compliance, medical imaging
- **Government**: Records management, public records, regulatory filings
- **Manufacturing**: Quality documentation, engineering drawings, compliance records

## Integration with AI Agents

ContentEdge can be integrated with AI agents through its MCP (Model Context Protocol) server, enabling:
- Natural language queries to search and retrieve documents
- Automated document archiving workflows
- Content class and index discovery
- Document version tracking
- Multilingual support for global organizations

## ContentEdge Datasheet

A detailed product datasheet is available: **contentedge-unlock-maximum-value-datasheet.pdf**
This datasheet provides comprehensive information about ContentEdge features, benefits, deployment options, and technical specifications.

---

*ContentEdge by Rocket Software — Unlocking Maximum Value from Enterprise Content*
*For more information visit: https://www.rocketsoftware.com/en-us/products/contentedge*
