# Recursive Development Agent

A LangChain and LangGraph-powered agent that recursively develops and enhances software projects based on high-level user requests.

## Features

- Recursive project development through iterative improvements
- Automated code generation and analysis
- Project structure management
- State tracking and development history
- Intelligent enhancement suggestions

## Requirements

- Python 3.8+
- OpenAI API key
- Git (optional, for version control features)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/recursive-agent.git
cd recursive-agent
```

2. Copy the environment template and configure your settings:
```bash
cp .env.template .env
```

Edit `.env` and add your OpenAI API key and other configurations.

## Usage

The project includes a Makefile for common operations:

1. Initialize the environment (create virtual environment and install dependencies):
```bash
make init
```

2. Start the agent:
```bash
make run
```

3. Clean up generated files and virtual environment:
```bash
make clean
```

4. Run project tests:
```bash
make test
```

2. Enter your high-level project request, for example:
```
Enter your request: build a social media app
```

3. The agent will:
   - Analyze your request
   - Create a basic implementation
   - Recursively enhance the project
   - Keep you updated on progress
   - Continue until you're satisfied or type 'quit'

## Project Structure

```
recursive_agent/
├── src/
│   ├── agents/           # Agent implementations
│   │   ├── tools/       # Agent tools
│   │   └── base.py      # Base agent class
│   ├── workflows/        # LangGraph workflows
│   ├── config.py        # Configuration
│   └── main.py          # Entry point
├── memlog/              # Project state and history
├── tests/               # Test cases
├── .env.template        # Environment template
└── requirements.txt     # Dependencies
```

## Development Process

The agent follows a recursive development process:

1. **Analysis Phase**
   - Understand user requirements
   - Assess current project state
   - Identify core functionality

2. **Implementation Phase**
   - Generate initial code
   - Set up project structure
   - Implement basic features

3. **Enhancement Phase**
   - Analyze current implementation
   - Identify potential improvements
   - Plan and implement enhancements
   - Repeat until satisfied

4. **Validation Phase**
   - Test functionality
   - Verify requirements
   - Document changes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
