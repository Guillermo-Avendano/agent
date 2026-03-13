# Smart Chat AI Agent

## Overview

The Smart Chat AI Agent is an advanced automation system that extends the capabilities of the Content Repository Smart Chat API. It provides intelligent workflows, conversation management, and automated document processing capabilities.

## Features

### 🤖 Core Capabilities

- **Document Analysis**: Automated analysis of documents with different analysis types (financial, legal, technical, general)
- **Conversation Management**: Multi-turn conversations with context preservation
- **Search Optimization**: Intelligent search criteria optimization for better results
- **Content Classification**: Automated classification of documents into categories
- **Workflow Automation**: Execution of predefined workflows with customizable parameters

### 🔧 Technical Features

- **Background Processing**: Asynchronous task execution with queuing
- **State Management**: Real-time agent state tracking and monitoring
- **Performance Tracking**: Execution statistics and performance metrics
- **Error Handling**: Robust error handling and recovery mechanisms
- **Extensible Architecture**: Easy addition of new workflows and capabilities

## Architecture

### Core Components

```
SmartChatAgent
├── ContentSmartChat (API Integration)
├── Task Queue (Background Processing)
├── Workflow Engine (Workflow Execution)
├── Conversation Manager (Context Management)
└── Status Monitor (Performance Tracking)
```

### Agent States

- **IDLE**: Agent is ready to process tasks
- **PROCESSING**: Agent is currently executing a task
- **WAITING**: Agent is waiting for external input
- **ERROR**: Agent encountered an error
- **COMPLETED**: Task completed successfully

## Installation and Setup

### Prerequisites

- Python 3.7+
- Content Repository API access
- Required dependencies (see requirements.txt)

### Basic Setup

```python
from rocketcontent.content_services_api import ContentServicesApi
from rocketcontent.content_smart_chat_agent import SmartChatAgent

# Initialize Content Services API
content_obj = ContentServicesApi(config_file)

# Initialize AI Agent
agent = SmartChatAgent(content_obj.config, "MyAgent")
```

## Usage Examples

### 1. Document Analysis

```python
# Analyze financial documents
task_data = {
    'search_criteria': [
        {'index_name': 'CUST_ID', 'operator': 'EQ', 'index_value': '1000'}
    ],
    'analysis_type': 'financial',
    'custom_query': 'Analyze the loan application documents'
}

task_id = agent.submit_task(AgentTask.DOCUMENT_ANALYSIS, task_data)
result = agent.get_task_result(timeout=30.0)

if result and result.success:
    print(f"Analysis completed: {result.data.get('summary', 'No summary')}")
```

### 2. Conversation Management

```python
# Start a conversation
conversation_id = "loan_app_001"

# First query
task_data = {
    'conversation_id': conversation_id,
    'query': 'Who is the loan applicant?',
    'document_ids': None
}

task_id = agent.submit_task(AgentTask.CONVERSATION_MANAGEMENT, task_data)
result = agent.get_task_result(timeout=30.0)

# Follow-up query with context
task_data = {
    'conversation_id': conversation_id,
    'query': 'What are the financial details?',
    'document_ids': None
}

task_id = agent.submit_task(AgentTask.CONVERSATION_MANAGEMENT, task_data)
result = agent.get_task_result(timeout=30.0)
```

### 3. Search Optimization

```python
# Optimize search criteria
task_data = {
    'search_criteria': [
        {'index_name': 'CUST_ID', 'operator': 'EQ', 'index_value': '1000'},
        {'index_name': 'FName', 'operator': 'EQ', 'index_value': 'John'}
    ],
    'optimization_type': 'relevance'
}

task_id = agent.submit_task(AgentTask.SEARCH_OPTIMIZATION, task_data)
result = agent.get_task_result(timeout=30.0)
```

### 4. Content Classification

```python
# Classify documents
task_data = {
    'classification_criteria': [
        {'index_name': 'CUST_ID', 'operator': 'EQ', 'index_value': '1000'}
    ],
    'target_categories': ['Financial Documents', 'Legal Documents', 'Personal Information']
}

task_id = agent.submit_task(AgentTask.CONTENT_CLASSIFICATION, task_data)
result = agent.get_task_result(timeout=30.0)
```

## Workflows

### Default Workflows

The agent comes with several pre-configured workflows:

#### 1. Document Analysis Workflow
- **Purpose**: Analyze documents and extract key information
- **Steps**: Search → Analyze → Extract → Summarize
- **Duration**: ~30 seconds
- **Priority**: Medium

#### 2. Conversation Management Workflow
- **Purpose**: Manage multi-turn conversations with context
- **Steps**: Initialize → Process → Maintain → Generate
- **Duration**: ~15 seconds
- **Priority**: High

#### 3. Content Classification Workflow
- **Purpose**: Classify documents into categories
- **Steps**: Search → Analyze → Determine → Apply
- **Duration**: ~45 seconds
- **Priority**: Medium

### Custom Workflows

You can create custom workflows by defining `AgentWorkflow` objects:

```python
from rocketcontent.content_smart_chat_agent import AgentWorkflow

custom_workflow = AgentWorkflow(
    name="Custom Analysis",
    description="Custom document analysis workflow",
    steps=[
        {"action": "search_documents", "description": "Search for documents"},
        {"action": "custom_analysis", "description": "Perform custom analysis"},
        {"action": "generate_report", "description": "Generate analysis report"}
    ],
    required_parameters=["search_criteria", "analysis_type"],
    estimated_duration=60,
    priority=3
)

agent.add_workflow(custom_workflow)
```

## Interfaces

### 1. Command Line Interface (CLI)

Run the interactive CLI:

```bash
python dev/13_smart_chat_agent_cli.py
```

**Available Commands:**
- `help` - Show help information
- `status` - Show agent status
- `chat <question>` - Send a chat question
- `workflow <type> <args>` - Execute a workflow
- `conversation <id>` - Set conversation ID
- `history` - Show conversation history
- `workflows` - List available workflows

**Example CLI Session:**
```
[CLIAgent]> status
[CLIAgent]> chat "Who is the loan applicant?"
[CLIAgent]> workflow document_analysis CUST_ID=1000 financial
[CLIAgent]> history
```

### 2. Graphical User Interface (GUI)

Run the GUI application:

```bash
python apps/ES_logs/SmartChat/smart_chat_agent_gui.py
```

**GUI Features:**
- Tabbed interface for different functions
- Real-time chat interface
- Workflow execution panel
- Agent status monitoring
- Conversation history viewer

### 3. Programmatic API

Use the agent directly in your Python code:

```python
# Initialize agent
agent = SmartChatAgent(content_config, "MyAgent")

# Submit tasks
task_id = agent.submit_task(AgentTask.DOCUMENT_ANALYSIS, task_data)

# Get results
result = agent.get_task_result(timeout=30.0)

# Monitor status
status = agent.get_agent_status()
```

## Configuration

### Agent Configuration

The agent uses the same configuration as the Content Services API:

```yaml
# rocketcontent.yaml
url: "https://your-content-repository.com"
repo_name: "Your Repository"
log_level: "INFO"
log_file: "agent.log"
```

### Environment Variables

- `CONTENT_CONFIG`: Path to configuration file (optional)

## Monitoring and Statistics

### Agent Status

Get comprehensive agent status:

```python
status = agent.get_agent_status()
print(f"Agent State: {status['state']}")
print(f"Queue Size: {status['queue_size']}")
print(f"Execution Stats: {status['execution_stats']}")
```

### Performance Metrics

The agent tracks various performance metrics:

- **Total Queries**: Number of queries processed
- **Successful Queries**: Number of successful queries
- **Failed Queries**: Number of failed queries
- **Average Response Time**: Average execution time

### Conversation History

Manage conversation history:

```python
# Get conversation history
history = agent.get_conversation_history(conversation_id)

# Clear conversation history
agent.clear_conversation_history(conversation_id)
```

## Error Handling

### Common Errors

1. **Initialization Errors**: Check configuration and API connectivity
2. **Task Submission Errors**: Verify task data format
3. **Timeout Errors**: Increase timeout values for long-running tasks
4. **API Errors**: Check Content Repository API status

### Error Recovery

The agent includes automatic error recovery:

- **Retry Logic**: Automatic retry for transient failures
- **State Recovery**: Agent state recovery after errors
- **Error Logging**: Comprehensive error logging for debugging

## Best Practices

### 1. Task Management

- Use appropriate timeouts for different task types
- Monitor task queue size to prevent overload
- Handle task results asynchronously when possible

### 2. Conversation Management

- Use consistent conversation IDs for related queries
- Clear conversation history when starting new topics
- Monitor conversation context size

### 3. Performance Optimization

- Use specific search criteria to reduce processing time
- Batch related tasks when possible
- Monitor agent performance metrics

### 4. Error Handling

- Always check task results for success/failure
- Implement proper error handling in your applications
- Log errors for debugging and monitoring

## Troubleshooting

### Common Issues

1. **Agent Not Initializing**
   - Check configuration file path
   - Verify API connectivity
   - Check log files for errors

2. **Tasks Not Completing**
   - Check timeout values
   - Verify task data format
   - Monitor agent state

3. **Poor Performance**
   - Optimize search criteria
   - Reduce task queue size
   - Monitor execution statistics

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Reference

### SmartChatAgent Class

#### Methods

- `__init__(content_config, agent_name)`: Initialize agent
- `submit_task(task_type, task_data)`: Submit a task for processing
- `get_task_result(timeout)`: Get next available task result
- `get_agent_status()`: Get current agent status
- `add_workflow(workflow)`: Add a custom workflow
- `get_conversation_history(conversation_id)`: Get conversation history
- `clear_conversation_history(conversation_id)`: Clear conversation history

#### Properties

- `agent_name`: Agent identifier
- `state`: Current agent state
- `workflows`: Available workflows

### AgentTask Enum

- `DOCUMENT_ANALYSIS`: Document analysis tasks
- `CONVERSATION_MANAGEMENT`: Conversation management tasks
- `SEARCH_OPTIMIZATION`: Search optimization tasks
- `CONTENT_CLASSIFICATION`: Content classification tasks
- `WORKFLOW_AUTOMATION`: Workflow automation tasks

### AgentResponse Class

- `success`: Task success status
- `message`: Response message
- `data`: Response data
- `conversation_id`: Conversation identifier
- `workflow_id`: Workflow identifier
- `timestamp`: Response timestamp
- `execution_time`: Task execution time

## Future Enhancements

### Planned Features

1. **Advanced Workflows**: More sophisticated workflow definitions
2. **Machine Learning**: ML-powered document analysis
3. **Integration APIs**: REST API for external integration
4. **Dashboard**: Web-based monitoring dashboard
5. **Multi-Agent**: Support for multiple coordinated agents

### Extension Points

The agent is designed for easy extension:

- **Custom Workflows**: Add new workflow types
- **Custom Tasks**: Implement custom task types
- **Custom Handlers**: Add custom result handlers
- **Custom Monitoring**: Implement custom monitoring

## Support and Contributing

### Getting Help

- Check the documentation for common issues
- Review log files for error details
- Use the CLI help command for usage information

### Contributing

1. Follow the existing code style
2. Add comprehensive tests for new features
3. Update documentation for new capabilities
4. Submit pull requests for review

## License

This project follows the same license as the main Content Repository Python library.

---

## Índices Válidos y Validación Dinámica

El agente valida automáticamente los índices utilizados en los criterios de búsqueda para todos los workflows relevantes (análisis, clasificación, optimización, automatización). Solo se utilizan índices válidos definidos en el repositorio, extraídos dinámicamente al inicializar el agente.

- **¿Cómo funciona?**
  - Al iniciar, el agente exporta los índices y grupos de índices del repositorio y construye una lista interna de IDs válidos.
  - Antes de ejecutar cualquier búsqueda, filtra los criterios para usar solo índices válidos.
  - Si se intenta usar un índice inexistente, se muestra una advertencia en el log y ese criterio es ignorado.

- **Métodos públicos:**
  - `reload_valid_indexes()`: Recarga la lista de índices válidos dinámicamente (útil si el backend cambia).
  - `get_valid_indexes()`: Devuelve la lista de IDs de índices válidos actualmente cargados.

- **Ejemplo:**
```python
# Obtener lista de índices válidos
print(agent.get_valid_indexes())

# Forzar recarga de índices válidos
agent.reload_valid_indexes()
```

- **Advertencias:**
  - Si un criterio de búsqueda usa un índice no válido, se ignora y se muestra una advertencia en el log.

---

## Contexto Conversacional en Smart Chat

Para mantener el contexto en conversaciones multi-turno, debes usar el atributo `conversation` del objeto `SmartChatResponse`.

- **Flujo correcto:**
  1. Realiza la primera pregunta sin pasar conversation_id.
  2. Guarda el `conversation` de la respuesta.
  3. Para cada pregunta siguiente, pásalo como parámetro para mantener el contexto.

- **Ejemplo:**
```python
# Primera pregunta
response = content_obj.smart_chat("Who is the loan applicant?", document_ids)
conversation_id = response.conversation

# Segunda pregunta, manteniendo el contexto
response2 = content_obj.smart_chat("What are the financial details?", document_ids, conversation=conversation_id)
```

- **En el agente:**
  - El workflow de conversación (`CONVERSATION_MANAGEMENT`) maneja automáticamente el contexto y actualiza el conversation_id en cada respuesta.
  - El historial de conversación se guarda por ID.

---

## Troubleshooting y Notas de Robustez

- **Índices no válidos:** Si usas un índice inexistente, el agente lo ignora y lo reporta en el log. Usa `get_valid_indexes()` para consultar los válidos.
- **Contexto perdido:** Si no pasas el conversation_id en preguntas sucesivas, perderás el contexto. Siempre usa el conversation devuelto por la respuesta anterior.
- **Recarga de índices:** Si el backend cambia, llama a `reload_valid_indexes()` para actualizar la lista interna.

---

## Cambios recientes
- Validación automática y dinámica de índices en todos los workflows.
- Manejo robusto del contexto conversacional usando el atributo conversation.
- Métodos públicos para consultar y recargar índices válidos.
- Advertencias automáticas en el log para criterios ignorados.

*For more information, see the main Content Repository documentation and examples.* 