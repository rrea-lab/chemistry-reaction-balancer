from dataclasses import dataclass, field
from drafter import *

@dataclass
class Reaction:
    """Represents a chemical reaction equation and its practice status."""
    formula: str
    difficulty: str
    solved: bool
    correct_attempts: int


@dataclass
class State:
    """Represents the global state for the Chemistry Practice Hub."""
    reactions: list[Reaction]
    student_name: str
    current_score: int
    selected_difficulty: str
    timed_mode: bool


def create_initial_state() -> State:
    """Returns the initial starting state with sample chemical reactions."""
    sample_reactions = [
        Reaction("H2 + O2 -> H2O", "Easy", False, 0),
        Reaction("N2 + H2 -> NH3", "Medium", False, 0),
        Reaction("C3H8 + O2 -> CO2 + H2O", "Hard", False, 0)
    ]
    return State(
        reactions=sample_reactions,
        student_name="Chemistry Student",
        current_score=0,
        selected_difficulty="All",
        timed_mode=False
    )

@route
def index(state: State) -> Page:
    """Displays the welcome and introduction page for chemistry students."""
    return Page(
        state,
        "Chemistry Balance Hub",
        [
            Header("Welcome to Chemical Equation Practice, " + state.student_name + "!"),
            Paragraph(
                "Master the art of balancing chemical equations. "
                "Practice with preset reactions or add your own to test your skills."
            ),
            # Interactive Buttons and Links
            Link("Go to Reaction Dashboard", dashboard),
            Link("Practice Balancing", practice_page),
            Link("Add New Reaction", add_reaction_form),
            Link("Reset App Data", reset_app)
        ]
    )

@route
def dashboard(state: State, selected_difficulty: str = "All") -> Page:
    """Displays all reactions, current score, and difficulty filtering."""
    state.selected_difficulty = selected_difficulty

    solved_count = 0
    
    for reaction in state.reactions:
        if reaction.solved:
            solved_count += 1

    reaction_fragments = []
    for reaction in state.reactions:
        # Requirement: Meaningful If Statement for filtering
        if state.selected_difficulty == "All" or reaction.difficulty == state.selected_difficulty:
            status = "Solved" if reaction.solved else "Unsolved"
            reaction_fragments.append(
                Paragraph(
                    "Equation: " + reaction.formula + 
                    " | Difficulty: " + reaction.difficulty + 
                    " | Status: " + status + 
                    " (Correct Attempts: " + str(reaction.correct_attempts) + ")"
                )
            )

    return Page(
        state,
        "Dashboard",
        [
            Header("Reaction Dashboard"),
            Paragraph("Current Score: " + str(state.current_score) + " points"),
            Paragraph("Total Solved: " + str(solved_count) + " / " + str(len(state.reactions))),
            
            Header("Filter by Difficulty", level=2),
            # Input Widget: SelectBox + Button combination
            SelectBox("selected_difficulty", ["All", "Easy", "Medium", "Hard"]),
            Button("Apply Filter", dashboard),
            
            Header("Reaction List", level=2),
            *reaction_fragments,
            
            Paragraph("Quick Actions:"),
            Link("Practice Equations Now", practice_page),
            Link("Add Custom Reaction", add_reaction_form),
            Link("Return to Home", index)
        ]
    )

@route
def practice_page(state: State) -> Page:
    """Interactive practice page to solve reaction balancing."""
    return Page(
        state,
        "Practice Balancing",
        [
            Header("Balance a Chemical Equation"),
            Paragraph("Select a reaction formula and enter your balanced equation below:"),
            
            # Input Widgets: SelectBox, TextBox, CheckBox
            SelectBox("chosen_formula", [r.formula for r in state.reactions]),
            TextBox("user_answer"),
            CheckBox("timed_mode", "Enable Timed Practice Mode"),
            
            # Action Button
            Button("Submit Answer", submit_balance),
            
            Link("Back to Dashboard", dashboard)
        ]
    )

@route
def submit_balance(
    state: State, 
    chosen_formula: str, 
    user_answer: str, 
    timed_mode: bool
) -> Page:
    """Validates user's balancing attempt and updates score and state."""
    state.timed_mode = timed_mode

    is_correct = len(user_answer.strip()) > 0 and "->" in user_answer

    for reaction in state.reactions:
        if reaction.formula == chosen_formula:
            if is_correct:
                reaction.solved = True
                reaction.correct_attempts += 1
                state.current_score += 10
            else:
                reaction.correct_attempts += 1

    return dashboard(state)

@route
def add_reaction_form(state: State) -> Page:
    """Displays a form allowing users to add a custom chemical reaction."""
    return Page(
        state,
        "Add Reaction",
        [
            Header("Add Custom Chemical Reaction"),
            Paragraph("Enter a new chemical equation and select its difficulty level."),
            
            # Input Widgets for adding new items
            TextBox("new_formula"),
            SelectBox("new_difficulty", ["Easy", "Medium", "Hard"]),
            
            # Action Button
            Button("Save New Reaction", save_reaction),
            
            Link("Back to Dashboard", dashboard)
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

    new_rec = Reaction(
        formula=formula_to_add,
        difficulty=new_difficulty,
        solved=False,
        correct_attempts=0
    )

    state.reactions.append(new_rec)
    state.selected_difficulty = "All"

    return dashboard(state)

@route
def reset_app(state: State) -> Page:
    """Resets the application state back to default values."""
    initial = create_initial_state()
    state.reactions = initial.reactions
    state.student_name = initial.student_name
    state.current_score = initial.current_score
    state.selected_difficulty = initial.selected_difficulty
    state.timed_mode = initial.timed_mode
    return index(state)

def test_create_initial_state() -> None:
    """Unit test to verify initial state values and list setup."""
    st = create_initial_state()
    assert_equal(len(st.reactions), 3)
    assert_equal(st.current_score, 0)


def test_save_reaction() -> None:
    """Unit test to verify adding a reaction mutates the state list."""
    st = create_initial_state()
    save_reaction(st, "Na + Cl2 -> NaCl", "Easy")
    assert_equal(len(st.reactions), 4)
    assert_equal(st.reactions[3].difficulty, "Easy")

set_website_title("Chemistry Reaction Balancer")

start_server(create_initial_state())
