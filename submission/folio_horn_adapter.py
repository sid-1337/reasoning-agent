from __future__ import annotations

import re
from typing import Optional

from logic_engine import Atom, HornRule, make_knowledge_base, forward_chain, unify


class UnsupportedFormula(ValueError):
    pass


def _strip_outer(text: str) -> str:
    text = text.strip()
    while text.startswith("(") and text.endswith(")"):
        depth = 0
        encloses_all = True
        for index, character in enumerate(text):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0 and index != len(text) - 1:
                    encloses_all = False
                    break
        if not encloses_all or depth != 0:
            break
        text = text[1:-1].strip()
    return text


def _split_top_level(text: str, operator: str) -> list[str]:
    parts = []
    depth = 0
    start = 0
    index = 0
    while index < len(text):
        character = text[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                raise UnsupportedFormula("Unbalanced parentheses")
        elif depth == 0 and text.startswith(operator, index):
            parts.append(text[start:index].strip())
            index += len(operator)
            start = index
            continue
        index += 1
    if depth != 0:
        raise UnsupportedFormula("Unbalanced parentheses")
    parts.append(text[start:].strip())
    return parts


def _parse_literal(text: str, variable_terms: dict[str, str]) -> Atom:
    text = _strip_outer(text)
    negated = text.startswith("¬")
    if negated:
        text = _strip_outer(text[1:].strip())
    match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_]*)\((.*)\)", text)
    if not match:
        raise UnsupportedFormula(f"Not an atomic predicate: {text}")

    predicate, argument_text = match.groups()
    arguments = []
    for argument in _split_top_level(argument_text, ","):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", argument):
            raise UnsupportedFormula(f"Unsupported term: {argument}")
        lowered = argument.lower()
        if lowered in variable_terms:
            arguments.append(variable_terms[lowered])
        elif lowered in {"x", "y", "z"}:
            raise UnsupportedFormula(f"Unbound variable: {argument}")
        else:
            arguments.append(lowered)
    return Atom(predicate.lower(), tuple(arguments), negated)


def _parse_conjunction(text: str, variable_terms: dict[str, str]) -> list[Atom]:
    parts = _split_top_level(_strip_outer(text), "∧")
    return [_parse_literal(part, variable_terms) for part in parts]


def _remove_universal_prefix(text: str) -> tuple[str, set[str]]:
    bound_variables = set()
    remaining = text.strip()
    while remaining.startswith("∀"):
        match = re.match(r"^∀\s*([A-Za-z])\s*", remaining)
        if not match:
            raise UnsupportedFormula("Malformed universal quantifier")
        bound_variables.add(match.group(1).lower())
        remaining = remaining[match.end():].strip()
    if "∀" in remaining or "∃" in remaining:
        raise UnsupportedFormula("Nested or existential quantifiers are unsupported")
    return _strip_outer(remaining), bound_variables


def _parse_existential_prefix(text: str, variable_term: str) -> tuple[str, dict[str, str]]:
    remaining = text.strip()
    match = re.match(r"^∃\s*([A-Za-z])\s*", remaining)
    if not match:
        raise UnsupportedFormula("Malformed existential quantifier")
    variable = match.group(1).lower()
    remaining = remaining[match.end():].strip()
    if "∃" in remaining or "∀" in remaining:
        raise UnsupportedFormula("Nested quantifiers are unsupported")
    return _strip_outer(remaining), {variable: variable_term}


def parse_premises(text: str) -> tuple[list[Atom], list[HornRule]]:
    facts: list[Atom] = []
    rules: list[HornRule] = []
    witness_index = 0
    for formula in (line.strip() for line in text.splitlines() if line.strip()):
        if any(operator in formula for operator in ("∃", "∨", "⊕", "↔")):
            if any(operator in formula for operator in ("∨", "⊕", "↔")):
                raise UnsupportedFormula(f"Unsupported connective in: {formula}")
            if formula.startswith("∃"):
                formula, variable_terms = _parse_existential_prefix(formula, f"__witness_{witness_index}")
                witness_index += 1
                if "→" in formula:
                    raise UnsupportedFormula("Existential implications are unsupported")
                facts.extend(_parse_conjunction(formula, variable_terms))
                continue
            raise UnsupportedFormula(f"Unsupported quantifier in: {formula}")
        formula, bound_variables = _remove_universal_prefix(formula)
        variable_terms = {variable: f"?{variable}" for variable in bound_variables}
        implication = _split_top_level(formula, "→")
        if len(implication) == 2:
            body = _parse_conjunction(implication[0], variable_terms)
            head = _parse_conjunction(implication[1], variable_terms)
            if not body or not head:
                raise UnsupportedFormula("Empty implication side")
            rules.extend(HornRule(tuple(body), atom) for atom in head)
        elif len(implication) == 1:
            parsed_facts = _parse_conjunction(formula, variable_terms)
            if bound_variables or any(term.startswith("?") for atom in parsed_facts for term in atom.arguments):
                raise UnsupportedFormula("Variable-containing facts are unsupported")
            facts.extend(parsed_facts)
        else:
            raise UnsupportedFormula("Nested implications are unsupported")
    return facts, rules


def _parse_query(text: str) -> tuple[list[Atom], Optional[tuple[list[Atom], list[Atom]]]]:
    if any(operator in text for operator in ("∀", "∨", "⊕", "↔")):
        raise UnsupportedFormula("Universally quantified or non-Horn query is unsupported")
    if text.strip().startswith("∃"):
        formula, variable_terms = _parse_existential_prefix(text, "?existential")
    else:
        if "∃" in text:
            raise UnsupportedFormula("Nested existential queries are unsupported")
        formula, bound_variables = _remove_universal_prefix(text)
        if bound_variables:
            raise UnsupportedFormula("Universally quantified queries are unsupported")
        variable_terms = {}
    implication = _split_top_level(formula, "→")
    if len(implication) == 2:
        if variable_terms:
            raise UnsupportedFormula("Existential implication queries are unsupported")
        antecedent = _parse_conjunction(implication[0], {})
        consequent = _parse_conjunction(implication[1], {})
        return [], (antecedent, consequent)
    if len(implication) == 1:
        return _parse_conjunction(formula, variable_terms), None
    raise UnsupportedFormula("Nested implications are unsupported")


def entails(premises_text: str, conclusion_text: str) -> tuple[bool, list[str]]:
    facts, rules = parse_premises(premises_text)
    query_atoms, query_implication = _parse_query(conclusion_text)
    if query_implication is not None:
        antecedent, query_atoms = query_implication
        if any(term.startswith("?") for atom in antecedent for term in atom.arguments):
            raise UnsupportedFormula("Variable-containing implication query is unsupported")
        facts.extend(antecedent)

    closure, trace = forward_chain(make_knowledge_base(facts, rules))

    def match_query(index: int, bindings: dict[str, str]) -> bool:
        if index == len(query_atoms):
            return True
        return any(
            (next_bindings := unify(query_atoms[index], fact, bindings)) is not None
            and match_query(index + 1, next_bindings)
            for fact in closure
        )

    return match_query(0, {}), [
        f"{rule} ==> {conclusion}" for rule, conclusion in trace
    ]
