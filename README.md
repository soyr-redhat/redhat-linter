# RHEA (Red Hat Editorial Auditor)

RHEA is an editorial tool for auditing technical content against Red Hat brand voice standards. This application uses Ollama and Model Context Protocol (MCP) to provide real-time, rule-based rewriting suggestions.

## Prerequisites

- **Ollama**: Must be installed and running locally. [Download here](https://ollama.com).
- **Python 3.10+**: Managed automatically via the startup script.

## Quick Start

The project is designed for a "zero-config" experience. Simply clone and run:

```bash
git clone https://github.com/soyr-redhat/redhat-linter
cd RedHatLinter
./startup.sh
```
If you're running into issues with running startup.sh, try to run
```bash 
chmod +x startup.sh
```
To guarantee the script is executable.
