
@function_tool
def solve_equation(equation: str) -> str:
    return str(eval(equation))

from agents import Agent

agent = Agent(
    name="Math Solver",
    instructions="You solve math problems by evaluating them with python and returning the result",
    tools=[solve_equation],
)