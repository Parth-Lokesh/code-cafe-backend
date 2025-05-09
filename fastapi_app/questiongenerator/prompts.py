coding_prompt = """
    Generate a simple to medium difficulty coding question.

    Include:
    1. Only 2 sample test cases (used for visible testing), in this format:
    Input: <input>
    Expected Output: <output>

    2. The output datatype (one of: "int", "str", "float", "bool", "list[int]", "list[str]", etc).

    3. Boilerplate code for three languages (Python, Java, C++):

    For each language, provide:
    - A function or class definition named appropriately where the user will write the logic.
    - A main function that runs exactly 10 hardcoded test cases.
    - The test cases (inputs and expected outputs) must be hardcoded into arrays/lists.
    - The main function must loop through the test cases, calling the user function and comparing outputs.
        - If all outputs match, print: "true"
        - If any test fails, print: "false-<i>" (1-based index of the failed test case) and stop checking further.

    Other constraints:
    - Do not include solution logic anywhere — only skeletons/placeholders.
    - In Java, import all required libraries in the Main class (not in the Solution class).
    - In Python, use `if __name__ == '__main__'`.
    - In C++, use `int main()` with input/output and call to solve().

    Respond strictly in JSON format like:
    {
    "question": "...",
    "test_cases": [
        { "input": "5", "output": "True" },
        { "input": "4", "output": "False" }
    ],
    "output_datatype": "bool",
    "boilerplate_code_user": {
        "python": "def solve(...):\\n    # your code here",
        "java": "public class Solution {\\n    // your code here\\n}",
        "c++": "#include <iostream>\\nusing namespace std;\\n\\nvoid solve() {\\n    // your code here\\n}"
    },
    "boilerplate_code_main": {
        "python": "if __name__ == '__main__':\\n    # input/output and solve() calls",
        "java": "import java.util.*;\\npublic class Main {\\n    public static void main(String[] args) {\\n        // input/output and call Solution methods\\n    }\\n}",
        "c++": "#include <iostream>\\nusing namespace std;\\n\\nint main() {\\n    // input/output and solve() calls\\n    return 0;\\n}"
    }
    }
    """

debugging_prompt = """
    Generate a simple to medium difficulty debugging question.

    Include:
    1. Only 2 sample test cases (used for visible testing), in this format:
    Input: <input>
    Expected Output: <output>

    2. The output datatype (one of: "int", "str", "float", "bool", "list[int]", "list[str]", etc).

    3. Boilerplate code for three languages (Python, Java, C++):

    For each language, provide:
    - A function or class definition that *contains the full logic* of the problem — BUT introduce 2-3 small bugs or logical errors (like off-by-one, wrong operator, missing condition, etc).
    - A main function that runs exactly 10 hardcoded test cases.
    - The test cases (inputs and expected outputs) must be hardcoded into arrays/lists.
    - The main function must loop through the test cases, calling the buggy user function and comparing outputs.
        - If all outputs match, print: "true"
        - If any test fails, print: "false-<i>" (1-based index of the failed test case) and stop checking further.

    Other constraints:
    - Do NOT tell what the bugs are — the user must find and fix them.
    - In Java, import all required libraries in the Main class (not in the Solution class).
    - In Python, use `if __name__ == '__main__'`.
    - In C++, use `int main()` with input/output and call to solve().

    Respond strictly in JSON format like:
    {
    "question": "...",
    "test_cases": [
        { "input": "5", "output": "True" },
        { "input": "4", "output": "False" }
    ],
    "output_datatype": "bool",
    "boilerplate_code_user": {
        "python": "def solve(...):\\n    # buggy logic here",
        "java": "public class Solution {\\n    // buggy logic here\\n}",
        "c++": "#include <iostream>\\nusing namespace std;\\n\\nvoid solve() {\\n    // buggy logic here\\n}"
    },
    "boilerplate_code_main": {
        "python": "if __name__ == '__main__':\\n    # input/output and solve() calls",
        "java": "import java.util.*;\\npublic class Main {\\n    public static void main(String[] args) {\\n        // input/output and call Solution methods\\n    }\\n}",
        "c++": "#include <iostream>\\nusing namespace std;\\n\\nint main() {\\n    // input/output and solve() calls\\n    return 0;\\n}"
    }
    }
    """
