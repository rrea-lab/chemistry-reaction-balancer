from dataclasses import dataclass
from drafter import *
import time
import random

MAX_SPECIES = 5          # most molecules per equation the practice page supports
TIMED_BONUS_SECONDS = 30  # answer this fast in timed mode for a bonus

EXAMPLE_REACTIONS = [
    ("Na + Cl2 -> NaCl", "Easy"),
    ("Mg + O2 -> MgO", "Easy"),
    ("Fe + O2 -> Fe2O3", "Medium"),
    ("CH4 + O2 -> CO2 + H2O", "Medium"),
    ("Al + HCl -> AlCl3 + H2", "Medium"),
    ("C2H6 + O2 -> CO2 + H2O", "Hard"),
    ("Ca(OH)2 + H3PO4 -> Ca3(PO4)2 + H2O", "Hard"),
    ("KMnO4 + HCl -> KCl + MnCl2 + H2O + Cl2", "Hard"),
]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class Reaction:
    """Represents a chemical reaction equation and its practice status."""
    formula: str
    difficulty: str
    solved: bool
    correct_attempts: int
    wrong_attempts: int
    solution: list[int]


@dataclass
class State:
    """Represents the global state for the Chemistry Practice Hub."""
    reactions: list[Reaction]
    student_name: str
    current_score: int
    selected_difficulty: str
    timed_mode: bool
    current_index: int
    streak: int
    best_streak: int
    hints_used: int
    start_time: float
    guess: list[str]
    feedback: str
    atom_report: str


# ---------------------------------------------------------------------------
# Chemistry helpers
# ---------------------------------------------------------------------------

def read_number(text: str, i: int) -> tuple[int, int]:
    """Reads an integer starting at position i. Returns (number, new_position).
    If there are no digits, the number is 1."""
    j = i
    while j < len(text) and text[j].isdigit():
        j += 1
    if j == i:
        return 1, i
    return int(text[i:j]), j


def parse_species(species: str) -> dict[str, int]:
    """Counts atoms in one molecule, e.g. 'Ca(OH)2' -> {'Ca': 1, 'O': 2, 'H': 2}."""
    stack = [{}]
    i = 0
    while i < len(species):
        ch = species[i]
        if ch in "([":
            stack.append({})
            i += 1
        elif ch in ")]":
            i += 1
            number, i = read_number(species, i)
            if len(stack) > 1:
                group = stack.pop()
                for element, count in group.items():
                    stack[-1][element] = stack[-1].get(element, 0) + count * number
        elif ch.isupper():
            j = i + 1
            while j < len(species) and species[j].islower():
                j += 1
            element = species[i:j]
            number, j = read_number(species, j)
            stack[-1][element] = stack[-1].get(element, 0) + number
            i = j
        else:
            i += 1
    return stack[0]


def split_equation(formula: str) -> tuple[list[str], list[str]]:
    """Splits 'H2 + O2 -> H2O' into (['H2', 'O2'], ['H2O'])."""
    if "->" not in formula:
        return [], []
    left, right = formula.split("->", 1)
    reactants = [s.strip() for s in left.split("+") if s.strip()]
    products = [s.strip() for s in right.split("+") if s.strip()]
    return reactants, products


def species_of(formula: str) -> list[str]:
    """All molecules in the equation, reactants first."""
    reactants, products = split_equation(formula)
    return reactants + products


def count_side(molecules: list[str], coefficients: list[int]) -> dict[str, int]:
    """Total atoms of each element on one side of the arrow."""
    totals = {}
    for molecule, coefficient in zip(molecules, coefficients):
        for element, count in parse_species(molecule).items():
            totals[element] = totals.get(element, 0) + count * coefficient
    return totals


def is_balanced(formula: str, coefficients: list[int]) -> bool:
    """True if the coefficients balance the equation."""
    reactants, products = split_equation(formula)
    if len(reactants) == 0 or len(products) == 0:
        return False
    if len(coefficients) != len(reactants) + len(products):
        return False
    for c in coefficients:
        if c < 1:
            return False
    left = count_side(reactants, coefficients[:len(reactants)])
    right = count_side(products, coefficients[len(reactants):])
    return left == right


def all_coefficients(n: int, top: int) -> list[list[int]]:
    """Every list of n whole numbers from 1 to top (like itertools.product)."""
    combos = [[]]
    for _ in range(n):
        bigger = []
        for combo in combos:
            for value in range(1, top + 1):
                bigger.append(combo + [value])
        combos = bigger
    return combos


def find_solution(formula: str) -> list[int]:
    """Finds the smallest whole-number coefficients that balance the equation.
    Returns an empty list if none are found."""
    reactants, products = split_equation(formula)
    n = len(reactants) + len(products)
    if len(reactants) == 0 or len(products) == 0 or n > MAX_SPECIES:
        return []

    vectors = [parse_species(m) for m in reactants + products]
    elements = set()
    for vector in vectors:
        elements.update(vector.keys())
    sign = [1] * len(reactants) + [-1] * len(products)

    best = []
    best_sum = 10 ** 9
    for coefficients in all_coefficients(n, 10):
        total = sum(coefficients)
        if total >= best_sum:
            continue
        balanced = True
        for element in elements:
            net = 0
            for k in range(n):
                net += sign[k] * coefficients[k] * vectors[k].get(element, 0)
            if net != 0:
                balanced = False
                break
        if balanced:
            best = list(coefficients)
            best_sum = total
    return best


def format_equation(formula: str, coefficients: list[int]) -> str:
    """Builds a readable equation such as '2H2 + O2 -> 2H2O'."""
    reactants, products = split_equation(formula)
    molecules = reactants + products
    parts = []
    for coefficient, molecule in zip(coefficients, molecules):
        prefix = "" if coefficient == 1 else str(coefficient)
        parts.append(prefix + molecule)
    left = " + ".join(parts[:len(reactants)])
    right = " + ".join(parts[len(reactants):])
    return left + " -> " + right


def parse_guess(texts: list[str], count: int) -> list[int]:
    """Converts the text boxes into integers. Bad input becomes 0 (invalid)."""
    result = []
    for k in range(count):
        try:
            result.append(int(texts[k].strip()))
        except (ValueError, IndexError):
            result.append(0)
    return result


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def make_reaction(formula: str, difficulty: str) -> Reaction:
    """Creates a Reaction and computes its answer key."""
    return Reaction(formula, difficulty, False, 0, 0, find_solution(formula))


def create_initial_state() -> State:
    """Returns the initial starting state with sample chemical reactions."""
    sample_reactions = [
        make_reaction("H2 + O2 -> H2O", "Easy"),
        make_reaction("N2 + H2 -> NH3", "Medium"),
        make_reaction("C3H8 + O2 -> CO2 + H2O", "Hard"),
    ]
    return State(
        reactions=sample_reactions,
        student_name="Chemistry Student",
        current_score=0,
        selected_difficulty="All",
        timed_mode=False,
        current_index=0,
        streak=0,
        best_streak=0,
        hints_used=0,
        start_time=time.time(),
        guess=["1", "1", "1", "1", "1"],
        feedback="",
        atom_report=""
    )


def visible_indices(state: State) -> list[int]:
    """Indices of reactions that match the current difficulty filter."""
    result = []
    for i, reaction in enumerate(state.reactions):
        if state.selected_difficulty == "All" or reaction.difficulty == state.selected_difficulty:
            result.append(i)
    return result


def start_attempt(state: State) -> None:
    """Clears the work area for a fresh attempt at the current reaction."""
    state.guess = ["1", "1", "1", "1", "1"]
    state.hints_used = 0
    state.feedback = ""
    state.atom_report = ""
    state.start_time = time.time()


def ensure_valid_index(state: State) -> None:
    """Keeps current_index pointing at a reaction that passes the filter."""
    indices = visible_indices(state)
    if len(indices) > 0 and state.current_index not in indices:
        state.current_index = indices[0]
        start_attempt(state)


def move(state: State, step: int) -> None:
    """Moves forward (+1) or backward (-1) through the filtered reactions."""
    indices = visible_indices(state)
    if len(indices) == 0:
        return
    if state.current_index in indices:
        position = (indices.index(state.current_index) + step) % len(indices)
        state.current_index = indices[position]
    else:
        state.current_index = indices[0]
    start_attempt(state)


def store_guess(state: State, c0: str, c1: str, c2: str, c3: str, c4: str, timed_mode: bool) -> None:
    """Saves what the student typed so it is still there after a button press."""
    state.guess = [c0, c1, c2, c3, c4]
    state.timed_mode = timed_mode


def current_reaction(state: State) -> Reaction:
    """The reaction being practiced (call only when reactions exist)."""
    return state.reactions[state.current_index]


# ---------------------------------------------------------------------------
# Pages: home
# ---------------------------------------------------------------------------

@route
def index(state: State) -> Page:
    """Displays the welcome page with quick-start buttons."""
    return Page(
        state,
        [
            Header("Welcome to Chemical Equation Practice, " + state.student_name + "!"),
            Paragraph(
                "Master the art of balancing chemical equations. "
                "Practice with preset reactions or add your own to test your skills."
            ),
            Paragraph("Score: " + str(state.current_score) + " | Current streak: " + str(state.streak)
                      + " | Best streak: " + str(state.best_streak)),

            Header("Get Started", level=2),
            Button("Start Practicing", start_practice),
            Button("Surprise Me (Random Reaction)", random_reaction),
            Button("View Dashboard", go_dashboard),
            Button("Add New Reaction", go_add_form),

            Header("Your Name", level=2),
            TextBox("new_name", state.student_name),
            Button("Save Name", set_name),

            Header("Start Over", level=2),
            Button("Reset Progress (keep reactions)", reset_progress),
            Button("Reset Everything", reset_app)
        ]
    )


@route
def set_name(state: State, new_name: str) -> Page:
    """Updates the student's name."""
    if new_name.strip() != "":
        state.student_name = new_name.strip()
    return index(state)


@route
def go_dashboard(state: State) -> Page:
    """Button target for the dashboard."""
    return dashboard(state, state.selected_difficulty)


@route
def go_add_form(state: State) -> Page:
    """Button target for the add-reaction form."""
    return add_reaction_form(state)


@route
def start_practice(state: State) -> Page:
    """Starts practicing from the first visible reaction."""
    indices = visible_indices(state)
    if len(indices) > 0:
        state.current_index = indices[0]
        start_attempt(state)
    return practice_page(state)


@route
def random_reaction(state: State) -> Page:
    """Jumps to a random reaction that matches the filter."""
    indices = visible_indices(state)
    if len(indices) > 0:
        state.current_index = random.choice(indices)
        start_attempt(state)
    return practice_page(state)


# ---------------------------------------------------------------------------
# Pages: dashboard
# ---------------------------------------------------------------------------

@route
def dashboard(state: State, selected_difficulty: str = "All") -> Page:
    """Displays all reactions, current score, and difficulty filtering."""
    state.selected_difficulty = selected_difficulty

    solved_count = 0
    total_correct = 0
    total_wrong = 0
    for reaction in state.reactions:
        if reaction.solved:
            solved_count += 1
        total_correct += reaction.correct_attempts
        total_wrong += reaction.wrong_attempts

    if total_correct + total_wrong > 0:
        accuracy = str(round(100 * total_correct / (total_correct + total_wrong))) + "%"
    else:
        accuracy = "no attempts yet"

    reaction_fragments = []
    for reaction in state.reactions:
        if state.selected_difficulty == "All" or reaction.difficulty == state.selected_difficulty:
            status = "Solved" if reaction.solved else "Unsolved"
            reaction_fragments.append(
                Paragraph(
                    "Equation: " + reaction.formula +
                    " | Difficulty: " + reaction.difficulty +
                    " | Status: " + status +
                    " | Correct: " + str(reaction.correct_attempts) +
                    " | Missed: " + str(reaction.wrong_attempts)
                )
            )
    if len(reaction_fragments) == 0:
        reaction_fragments.append(Paragraph("No reactions match this filter yet."))

    formulas = [r.formula for r in state.reactions]
    manage_widgets = []
    if len(formulas) > 0:
        manage_widgets = [
            Header("Manage a Reaction", level=2),
            SelectBox("manage_formula", formulas),
            Button("Practice This One", practice_selected),
            Button("Mark As Unsolved", mark_unsolved),
            Button("Delete This Reaction", delete_reaction),
        ]

    return Page(
        state,
        [
            Header("Reaction Dashboard"),
            Paragraph("Current Score: " + str(state.current_score) + " points"),
            Paragraph("Total Solved: " + str(solved_count) + " / " + str(len(state.reactions))),
            Paragraph("Streak: " + str(state.streak) + " (best: " + str(state.best_streak) + ")"),
            Paragraph("Accuracy: " + accuracy),

            Header("Filter by Difficulty", level=2),
            Paragraph("Showing: " + state.selected_difficulty),
            Button("Show All", filter_all),
            Button("Show Easy", filter_easy),
            Button("Show Medium", filter_medium),
            Button("Show Hard", filter_hard),
            SelectBox("selected_difficulty", ["All", "Easy", "Medium", "Hard"], state.selected_difficulty),
            Button("Apply Filter", dashboard),

            Header("Reaction List", level=2),
            *reaction_fragments,

            *manage_widgets,

            Header("Quick Actions", level=2),
            Button("Practice Equations Now", start_practice),
            Button("Random Reaction", random_reaction),
            Button("Add Custom Reaction", go_add_form),
            Button("Reset Progress", reset_progress),
            Link("Return to Home", index)
        ]
    )


@route
def filter_all(state: State) -> Page:
    """Filter button: all reactions."""
    return dashboard(state, "All")


@route
def filter_easy(state: State) -> Page:
    """Filter button: easy reactions."""
    return dashboard(state, "Easy")


@route
def filter_medium(state: State) -> Page:
    """Filter button: medium reactions."""
    return dashboard(state, "Medium")


@route
def filter_hard(state: State) -> Page:
    """Filter button: hard reactions."""
    return dashboard(state, "Hard")


@route
def practice_selected(state: State, manage_formula: str) -> Page:
    """Practice the reaction chosen in the manage menu."""
    for i, reaction in enumerate(state.reactions):
        if reaction.formula == manage_formula:
            state.current_index = i
            start_attempt(state)
    return practice_page(state)


@route
def mark_unsolved(state: State, manage_formula: str) -> Page:
    """Clears the solved flag for the chosen reaction."""
    for reaction in state.reactions:
        if reaction.formula == manage_formula:
            reaction.solved = False
    return dashboard(state, state.selected_difficulty)


@route
def delete_reaction(state: State, manage_formula: str) -> Page:
    """Removes the chosen reaction."""
    for i, reaction in enumerate(state.reactions):
        if reaction.formula == manage_formula:
            state.reactions.pop(i)
            break
    state.current_index = 0
    start_attempt(state)
    return dashboard(state, state.selected_difficulty)


# ---------------------------------------------------------------------------
# Pages: practice
# ---------------------------------------------------------------------------

@route
def practice_page(state: State) -> Page:
    """Interactive practice page: type a coefficient for every molecule."""
    ensure_valid_index(state)
    indices = visible_indices(state)

    if len(state.reactions) == 0 or len(indices) == 0:
        return Page(
            state,
            [
                Header("Nothing to practice yet"),
                Paragraph("There are no reactions for the filter '" + state.selected_difficulty + "'."),
                Button("Show All Difficulties", filter_all),
                Button("Add a Reaction", go_add_form),
                Link("Back to Home", index)
            ]
        )

    reaction = current_reaction(state)
    molecules = species_of(reaction.formula)
    count = len(molecules)

    position = indices.index(state.current_index) + 1

    # Live preview of what the student has typed so far
    preview_coefficients = parse_guess(state.guess, count)
    shown = []
    for c in preview_coefficients:
        shown.append(c if c >= 1 else 1)
    preview = format_equation(reaction.formula, shown)

    coefficient_widgets = []
    for k in range(count):
        coefficient_widgets.append(Paragraph("Coefficient for " + molecules[k] + ":"))
        coefficient_widgets.append(TextBox("coef" + str(k), state.guess[k]))

    extra_widgets = []
    if state.feedback != "":
        extra_widgets.append(Header("Feedback", level=2))
        extra_widgets.append(Paragraph(state.feedback))
    if state.atom_report != "":
        extra_widgets.append(Header("Atom Count", level=2))
        extra_widgets.append(Paragraph(state.atom_report))

    timer_note = ""
    if state.timed_mode:
        timer_note = ("Timed mode ON: check your answer within " + str(TIMED_BONUS_SECONDS) +
                      " seconds of loading this reaction for +5 bonus points.")

    return Page(
        state,
        [
            Header("Balance This Equation"),
            Paragraph("Reaction " + str(position) + " of " + str(len(indices)) +
                      " | Difficulty: " + reaction.difficulty +
                      " | Hints used: " + str(state.hints_used)),
            Header(reaction.formula, level=2),
            Paragraph("Enter a whole number (1 or more) for each molecule, then press Check Answer."),
            *coefficient_widgets,
            Paragraph("Your equation so far: " + preview),
            Paragraph("Timed Practice Mode (tick to enable):"),
            CheckBox("timed_mode", state.timed_mode),
            Paragraph(timer_note),

            Header("Actions", level=2),
            Button("Check Answer", check_answer),
            Button("Check Atom Count", check_atoms),
            Button("Get a Hint", get_hint),
            Button("Show Solution (no points)", show_solution),
            Button("Clear Inputs", clear_inputs),

            *extra_widgets,

            Header("Navigate", level=2),
            Button("Previous Reaction", previous_reaction),
            Button("Next Reaction", next_reaction),
            Button("Random Reaction", random_reaction),
            Button("Skip", next_reaction),
            Link("Back to Dashboard", go_dashboard)
        ]
    )


@route
def check_answer(
    state: State,
    coef0: str = "1", coef1: str = "1", coef2: str = "1", coef3: str = "1", coef4: str = "1",
    timed_mode: bool = False
) -> Page:
    """Validates the student's coefficients and updates score and state."""
    store_guess(state, coef0, coef1, coef2, coef3, coef4, timed_mode)
    reaction = current_reaction(state)
    count = len(species_of(reaction.formula))
    coefficients = parse_guess(state.guess, count)

    state.atom_report = ""
    if min(coefficients) < 1:
        state.feedback = "Every box needs a whole number of at least 1."
    elif is_balanced(reaction.formula, coefficients):
        points = max(2, 10 - 2 * state.hints_used)
        message = "Correct! " + format_equation(reaction.formula, coefficients)
        elapsed = time.time() - state.start_time
        if state.timed_mode and elapsed <= TIMED_BONUS_SECONDS:
            points += 5
            message += " (speed bonus!)"
        reaction.solved = True
        reaction.correct_attempts += 1
        state.current_score += points
        state.streak += 1
        if state.streak > state.best_streak:
            state.best_streak = state.streak
        state.feedback = message + " You earned " + str(points) + " points."
    else:
        reaction.wrong_attempts += 1
        state.streak = 0
        state.feedback = ("Not balanced yet. Try 'Check Atom Count' to see which "
                          "element is off, or ask for a hint.")
    return practice_page(state)


@route
def check_atoms(
    state: State,
    coef0: str = "1", coef1: str = "1", coef2: str = "1", coef3: str = "1", coef4: str = "1",
    timed_mode: bool = False
) -> Page:
    """Shows how many atoms of each element are on each side (no penalty)."""
    store_guess(state, coef0, coef1, coef2, coef3, coef4, timed_mode)
    reaction = current_reaction(state)
    reactants, products = split_equation(reaction.formula)
    coefficients = parse_guess(state.guess, len(reactants) + len(products))

    if min(coefficients) < 1:
        state.atom_report = "Enter whole numbers (1 or more) first."
    else:
        left = count_side(reactants, coefficients[:len(reactants)])
        right = count_side(products, coefficients[len(reactants):])
        elements = sorted(set(left.keys()) | set(right.keys()))
        lines = []
        for element in elements:
            l = left.get(element, 0)
            r = right.get(element, 0)
            mark = "OK" if l == r else "MISMATCH"
            lines.append(element + ": " + str(l) + " left vs " + str(r) + " right (" + mark + ")")
        state.atom_report = " | ".join(lines)
    return practice_page(state)


@route
def get_hint(
    state: State,
    coef0: str = "1", coef1: str = "1", coef2: str = "1", coef3: str = "1", coef4: str = "1",
    timed_mode: bool = False
) -> Page:
    """Gives progressively stronger hints. Each hint lowers the points available."""
    store_guess(state, coef0, coef1, coef2, coef3, coef4, timed_mode)
    reaction = current_reaction(state)
    state.hints_used += 1
    level = state.hints_used

    if level == 1:
        state.feedback = "Hint 1: List every element and count its atoms on both sides of the arrow."
    elif level == 2:
        state.feedback = ("Hint 2: Balance elements that appear in only one molecule per side first; "
                          "save O and H for last.")
    else:
        reveal = min(level - 2, len(reaction.solution))
        parts = []
        molecules = species_of(reaction.formula)
        for k in range(reveal):
            parts.append(molecules[k] + " = " + str(reaction.solution[k]))
        state.feedback = "Hint " + str(level) + ": " + ", ".join(parts)
    return practice_page(state)


@route
def show_solution(
    state: State,
    coef0: str = "1", coef1: str = "1", coef2: str = "1", coef3: str = "1", coef4: str = "1",
    timed_mode: bool = False
) -> Page:
    """Reveals the answer. No points, and the streak resets."""
    store_guess(state, coef0, coef1, coef2, coef3, coef4, timed_mode)
    reaction = current_reaction(state)
    state.streak = 0
    state.atom_report = ""
    if len(reaction.solution) == 0:
        state.feedback = "No answer key is stored for this equation."
    else:
        state.feedback = ("Solution: " + format_equation(reaction.formula, reaction.solution) +
                          ". Study it, then press Next Reaction.")
    return practice_page(state)


@route
def clear_inputs(state: State) -> Page:
    """Resets the coefficient boxes and feedback for this reaction."""
    start_attempt(state)
    return practice_page(state)


@route
def next_reaction(state: State) -> Page:
    """Go to the next reaction."""
    move(state, 1)
    return practice_page(state)


@route
def previous_reaction(state: State) -> Page:
    """Go to the previous reaction."""
    move(state, -1)
    return practice_page(state)


# ---------------------------------------------------------------------------
# Pages: add reactions
# ---------------------------------------------------------------------------

@route
def add_reaction_form(state: State) -> Page:
    """Displays a form allowing users to add a custom chemical reaction."""
    extra_widgets = []
    if state.feedback != "":
        extra_widgets.append(Paragraph(state.feedback))

    return Page(
        state,
        [
            Header("Add Custom Chemical Reaction"),
            Paragraph("Enter an UNBALANCED equation using '->' and '+', e.g. Al + O2 -> Al2O3. "
                      "Parentheses work too, e.g. Ca(OH)2. Up to " + str(MAX_SPECIES) +
                      " molecules. Do not type coefficients."),

            TextBox("new_formula"),
            SelectBox("new_difficulty", ["Easy", "Medium", "Hard"]),

            Button("Save New Reaction", save_reaction),
            Button("Add a Random Example", add_example),
            *extra_widgets,

            Link("Back to Dashboard", go_dashboard)
        ]
    )


@route
def save_reaction(
    state: State,
    new_formula: str,
    new_difficulty: str
) -> Page:
    """Validates and appends a new reaction dataclass instance to state."""
    if new_formula.strip() == "":
        formula_to_add = "H2 + Cl2 -> HCl"
    else:
        formula_to_add = new_formula.strip()

    reactants, products = split_equation(formula_to_add)
    if len(reactants) == 0 or len(products) == 0:
        state.feedback = "That doesn't look like an equation. Use the form: A + B -> C"
        return add_reaction_form(state)
    if len(reactants) + len(products) > MAX_SPECIES:
        state.feedback = "Please use at most " + str(MAX_SPECIES) + " molecules in total."
        return add_reaction_form(state)

    new_rec = make_reaction(formula_to_add, new_difficulty)
    if len(new_rec.solution) == 0:
        state.feedback = "This equation can't be balanced with small whole numbers. Check the formulas."
        return add_reaction_form(state)

    state.reactions.append(new_rec)
    state.selected_difficulty = "All"
    state.feedback = ""
    return dashboard(state)


@route
def add_example(state: State) -> Page:
    """Adds one example reaction that is not already in the list."""
    existing = [r.formula for r in state.reactions]
    options = []
    for formula, difficulty in EXAMPLE_REACTIONS:
        if formula not in existing:
            options.append((formula, difficulty))
    if len(options) == 0:
        state.feedback = "You've already added every example!"
        return add_reaction_form(state)
    formula, difficulty = random.choice(options)
    state.reactions.append(make_reaction(formula, difficulty))
    state.feedback = "Added: " + formula + " (" + difficulty + ")"
    return add_reaction_form(state)


# ---------------------------------------------------------------------------
# Pages: resets
# ---------------------------------------------------------------------------

@route
def reset_progress(state: State) -> Page:
    """Clears score and solved flags but keeps all reactions."""
    for reaction in state.reactions:
        reaction.solved = False
        reaction.correct_attempts = 0
        reaction.wrong_attempts = 0
    state.current_score = 0
    state.streak = 0
    state.best_streak = 0
    start_attempt(state)
    return index(state)


@route
def reset_app(state: State) -> Page:
    """Resets the application state back to default values."""
    initial = create_initial_state()
    state.reactions = initial.reactions
    state.student_name = initial.student_name
    state.current_score = initial.current_score
    state.selected_difficulty = initial.selected_difficulty
    state.timed_mode = initial.timed_mode
    state.current_index = initial.current_index
    state.streak = initial.streak
    state.best_streak = initial.best_streak
    state.hints_used = initial.hints_used
    state.start_time = initial.start_time
    state.guess = initial.guess
    state.feedback = initial.feedback
    state.atom_report = initial.atom_report
    return index(state)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_initial_state() -> None:
    """Unit test to verify initial state values and list setup."""
    st = create_initial_state()
    assert_equal(len(st.reactions), 3)
    assert_equal(st.current_score, 0)


def test_parse_species() -> None:
    """Unit test for atom counting, including parentheses."""
    assert_equal(parse_species("H2O"), {"H": 2, "O": 1})
    assert_equal(parse_species("Ca(OH)2"), {"Ca": 1, "O": 2, "H": 2})


def test_find_solution() -> None:
    """Unit test that the solver balances known equations."""
    assert_equal(find_solution("H2 + O2 -> H2O"), [2, 1, 2])
    assert_equal(find_solution("N2 + H2 -> NH3"), [1, 3, 2])
    assert_equal(find_solution("C3H8 + O2 -> CO2 + H2O"), [1, 5, 3, 4])


def test_is_balanced() -> None:
    """Unit test for the balance checker."""
    assert_equal(is_balanced("H2 + O2 -> H2O", [2, 1, 2]), True)
    assert_equal(is_balanced("H2 + O2 -> H2O", [1, 1, 1]), False)


def test_save_reaction() -> None:
    """Unit test to verify adding a reaction mutates the state list."""
    st = create_initial_state()
    save_reaction(st, "Na + Cl2 -> NaCl", "Easy")
    assert_equal(len(st.reactions), 4)
    assert_equal(st.reactions[3].difficulty, "Easy")
    assert_equal(st.reactions[3].solution, [2, 1, 2])


def test_check_answer() -> None:
    """Unit test that a correct answer scores points and a wrong one resets the streak."""
    st = create_initial_state()
    check_answer(st, "2", "1", "2", "1", "1", False)
    assert_equal(st.reactions[0].solved, True)
    assert_equal(st.current_score, 10)
    assert_equal(st.streak, 1)
    check_answer(st, "1", "1", "1", "1", "1", False)
    assert_equal(st.streak, 0)


set_website_title("Chemistry Reaction Balancer")

start_server(create_initial_state())
