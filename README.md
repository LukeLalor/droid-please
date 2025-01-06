# Droid Please

A CLI tool to modify local files. It initializes knowledge per-project that is designed to be checked into version control.


## Why "Droid Please"?

There are lots of code assistants and IDEs out there. Why is _droid-please_ different?

LLM IDEs and other tools tend to live with the developer. This means they cannot specialize in a project. They need to
either be told explicitly by the dev the context for the problem, or at best use RAG to dynamically grab the context.

`droid-please` believes these resources should live alongside and be versioned with the project code like your .git
directory. The idea here being that LLMs are expensive, especially if we want to create agents that learn about a
project. Furthermore, this learning needs to change over time as the project evolves. There is no reason for each dev to
waste time and resources teaching their own personal LLM about a shared codebase. Moreover, when I pull in a change from somebody else, I
would like my coding assistant to already know how to work with these changes.

This improves performance, but it is also a more cost-effective model for a GenAI tool. It allows for
"expensive" project learning since it only needs to happen occasionally per project rather than on every completion.

### Approach
Currently, `droid learn` is a basic process that automatically "learns" by allowing the agent to read through the project file system
and save a project summary file that is injected into the `droid please` system prompt.

When using `droid please` the agent has access to the project summary and tools to manipulate the file system.

## Pre-requisites
### Robust Version Control
Before we get into this project at all, you should have a robust version control system in place. This project is about
letting AI Agents manage your projects, which means droid can modify files within your project. Eventually **🚨 Droid
will break something 🚨**, and when this happens the ability to revert those changes is paramount.

### Python 3.10
This project requires Python 3.10 or higher. You can download the latest version of Python from the [official website](https://www.python.org/downloads/).

### PIP
The Quickstart guide uses pip. You can install pip by following the instructions [here](https://pip.pypa.io/en/stable/installation/).

### Anthropic API Key
This project right now only runs with Anthropic. Get an API key from [Anthropic](https://www.anthropic.com/)

## Quick Start

### Installation
```bash
pip install droid-please --upgrade
```
This will install the `droid` CLI tool on your system. Let's make sure it's installed correctly by running:
```bash
droid --help
```

```
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ init       Initialize a new .droid directory in the current directory with required configuration files.                                                 │
│ learn      Analyze the project structure and learn about its organization and purpose. The summary will be saved to the config file for future reference.│
│ please     Ask the droid to do something.                                                                                                                │
│ continue   Continue a conversation with the droid. If no conversation file is provided, continues the most recent conversation.                          │
│ save       Save a version of the latest conversation. If no conversation file is provided, saves the most recent conversation.                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

> 🚨 You might need reset or restart your terminal to get the `droid` command to work.

Droid Please also contains (optional) completions:
```bash
droid --install-completion
```

### Initialize droid in your project
The first thing we need to do is initialize `droid` in your project. This creates a `.droid` directory with project-specific settings and helps the AI understand your project structure.
```bash
cd /path/to/your/git/project
droid init
```
```
Anthropic API key (optional): *****
Initialized project: /path/to/your/git/project/.droid
```
> If you don't have your API key set up yet, you will be prompted to set it up.

### Have droid learn about your project
```bash
droid learn
```

### Try it out!
```bash
droid please "Update (or create) my project's README" -i
```
> The `-i` flag is for interactive mode. This will allow you to continue a conversation with your agent without having to run additional commands.


## Contributing

Droid Please!

### Need Help?

- Open an issue for questions or problems

Thank you for taking a look at Droid Please! 🚀