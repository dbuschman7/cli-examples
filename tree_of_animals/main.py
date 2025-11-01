#!/usr/bin/env python3
"""
Tree of Animals Parser
Reads lines from a file and processes them through a pyparsing parser.
"""

import sys
import os
from pathlib import Path
from pyparsing import (
    ParserElement,
    ParseException,
    Word,
    alphas,
    alphanums,
    Literal,
    Optional,
    Regex,
    oneOf,
    Suppress,
    CaselessLiteral,
)


# Enable packrat parsing for better performance (optional)
ParserElement.enablePackrat()


# Top-level directory for the hierarchy
TOP_DIR = Path("top")


def ensure_directory(path):
    """Create directory if it doesn't exist."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    print(f"  📁 Ensured directory: {path}")


def create_file(path, content):
    """Create a file with the given content."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content + '\n')
    print(f"  📄 Created file: {path} with content: {content}")


def create_symlink(link_path, target_path):
    """Create a symbolic link."""
    link_path = Path(link_path)
    target_path = Path(target_path)

    # Create parent directory for the link
    link_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing symlink if it exists
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()

    # Create relative symlink
    link_path.symlink_to(target_path)
    print(f"  🔗 Created symlink: {link_path} -> {target_path}")


# Parse Actions
def action_there_exists(tokens):
    """
    Rule 1: "There exists <A>"
    Creates directory: top/<A>
    """
    entity = tokens['entity'].lower()
    print(f"Rule 1: There exists {entity}")
    ensure_directory(TOP_DIR / entity)
    return {'rule': 'exists', 'entity': entity}


def action_are(tokens):
    """
    Rule 2: "<A> are <B>"
    Creates directory: top/<B>/<A>
    """
    child = tokens['child'].lower()
    parent = tokens['parent'].lower()
    print(f"Rule 2: {child} are {parent}")
    ensure_directory(TOP_DIR / parent / child)
    return {'rule': 'are', 'child': child, 'parent': parent}


def action_have(tokens):
    """
    Rule 3: "<A> have <B>(<C> : <D>)"
    Creates file: top/<A>/<B> with contents "<C>: <D>"
    """
    entity = tokens['entity'].lower()
    attribute = tokens['attribute'].lower()
    key = tokens['key']
    value = tokens['value']
    print(f"Rule 3: {entity} have {attribute}({key}: {value})")

    file_path = TOP_DIR / entity / attribute
    content = f"{key}: {value}"
    create_file(file_path, content)
    return {'rule': 'have', 'entity': entity, 'attribute': attribute, 'key': key, 'value': value}


def action_eat(tokens):
    """
    Rule 4: "<A> eats <B>"
    Creates symlink: top/<A>/eats/<B> -> top/<B>
    """
    predator = tokens['predator'].lower()
    prey = tokens['prey'].lower()
    print(f"Rule 4: {predator} eat {prey}")

    link_path = TOP_DIR / predator / "eats" / prey
    target_path = Path("../../") / prey  # Relative path from top/<A>/eats/<B> to top/<B>
    create_symlink(link_path, target_path)
    return {'rule': 'eat', 'predator': predator, 'prey': prey}


def define_grammar():
    """
    Define the pyparsing grammar for 4 rules.
    """
    # Common elements - entity/attribute names can include letters, numbers, and underscores
    entity_name = Word(alphas, alphas + alphanums + "_")

    # Rule 1: "There exists <A>"
    rule1 = (
        CaselessLiteral("There") + CaselessLiteral("exists") +
        entity_name("entity")
    ).setParseAction(action_there_exists)

    # Rule 2: "<A> are <B>"
    rule2 = (
        entity_name("child") +
        CaselessLiteral("are") +
        entity_name("parent")
    ).setParseAction(action_are)

    # Rule 3: "<A> have <B>(<C> : <D>)" or "<A> have <B>(<C>:<D>)" or "<A> have <B>(<C>=<D>)"
    # Key-value pair with flexible separators (: or = with optional spaces)
    key = Word(alphas, alphas + alphanums + "_")("key")
    value = Word(alphanums + "_")("value")
    separator = Suppress(Optional(" ")) + (Literal(":") | Literal("=")) + Suppress(Optional(" "))

    rule3 = (
        entity_name("entity") +
        CaselessLiteral("have") +
        entity_name("attribute") +
        Suppress("(") +
        key + separator + value +
        Suppress(")")
    ).setParseAction(action_have)

    # Rule 4: "<A> eats <B>" or "<A> eat <B>"
    rule4 = (
        entity_name("predator") +
        (CaselessLiteral("eats") | CaselessLiteral("eat")) +
        entity_name("prey")
    ).setParseAction(action_eat)

    # Combine all rules with | (or)
    parser = rule1 | rule2 | rule3 | rule4

    return parser


def parse_action_placeholder(tokens):
    """
    Parse action to be called when a pattern is matched.
    TODO: Implement your parse action logic here.

    Args:
        tokens: ParseResults object containing matched tokens
    """
    print(f"Matched tokens: {tokens}")
    # Add your action logic here
    pass


def process_line(parser, line_number, line):
    """
    Process a single line through the parser.

    Args:
        parser: The pyparsing parser
        line_number: Line number for error reporting
        line: The line content to parse

    Returns:
        Parsed result or None if parsing fails
    """
    try:
        result = parser.parseString(line, parseAll=True)
        return result
    except ParseException as pe:
        print(f"Parse error on line {line_number}: {pe}", file=sys.stderr)
        print(f"  Line content: {line}", file=sys.stderr)
        return None


def parse_file(filename):
    """
    Read and parse lines from a file.

    Args:
        filename: Path to the input file

    Returns:
        List of parsed results
    """
    parser = define_grammar()

    if parser is None:
        print("Error: Parser grammar not defined yet!", file=sys.stderr)
        return []

    # Attach parse actions
    # parser.setParseAction(parse_action_placeholder)

    results = []

    try:
        with open(filename, 'r') as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                result = process_line(parser, line_number, line)
                if result is not None:
                    results.append(result)

    except FileNotFoundError:
        print(f"Error: File '{filename}' not found!", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading file '{filename}': {e}", file=sys.stderr)
        sys.exit(1)

    return results


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input_file>", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]

    print(f"Parsing file: {input_file}")
    results = parse_file(input_file)

    print(f"\nSuccessfully parsed {len(results)} lines")

    # TODO: Process results as needed
    for i, result in enumerate(results, start=1):
        print(f"Result {i}: {result}")


if __name__ == "__main__":
    main()
