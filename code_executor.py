import bpy
import sys
import traceback
import builtins
import ast
from io import StringIO

class CodeExecutor:
    def __init__(self):
        # Only allow these modules and builtins!
        self.allowed_modules = {
            'bpy', 'bmesh', 'mathutils', 'math', 'random',
            'numpy', 'json', 're', 'time', 'datetime'
        }
        self.allowed_builtins = {
            'abs', 'all', 'any', 'bin', 'bool', 'callable', 'chr', 'complex', 'dict', 'dir', 'divmod',
            'enumerate', 'filter', 'float', 'format', 'frozenset', 'getattr', 'hasattr', 'hash', 'hex',
            'id', 'int', 'isinstance', 'issubclass', 'iter', 'len', 'list', 'map', 'max', 'min', 'next',
            'object', 'oct', 'ord', 'pow', 'print', 'range', 'repr', 'reversed', 'round', 'set', 'slice',
            'sorted', 'str', 'sum', 'tuple', 'type', 'zip'
        }

    def validate_code(self, code):
        """
        Use AST parsing to detect dangerous statements (import, exec, eval, etc).
        Returns (is_safe: bool, message: str)
        """
        try:
            tree = ast.parse(code, mode='exec')
        except Exception as ex:
            return False, f"Code could not be parsed: {ex}"

        for node in ast.walk(tree):
            # Block all import statements
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return False, "Imports are not allowed!"
            # Block exec, eval, compile, open, input, etc.
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['exec', 'eval', 'compile', 'open', 'input', 'raw_input', '__import__']:
                        return False, f"Usage of dangerous function '{node.func.id}' detected!"
            # Block access to dunder attributes
            if isinstance(node, ast.Attribute):
                if node.attr.startswith("__"):
                    return False, f"Access to dunder attribute '{node.attr}' is not allowed!"
            # Block global/locals manipulation
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                return False, "Global and nonlocal declarations are not allowed!"

        # All checks passed
        return True, "Code appears safe"

    def execute_code(self, code):
        """
        Executes validated code in a restricted environment.
        Returns: (success: bool, message: str, output: str)
        """
        # Step 1: Validate code
        is_safe, message = self.validate_code(code)
        if not is_safe:
            return False, message, ""

        # Step 2: Prepare restricted globals
        exec_globals = {
            'bpy': bpy,
            'bmesh': __import__('bmesh'),
            'mathutils': __import__('mathutils'),
            'math': __import__('math'),
            'random': __import__('random'),
            'json': __import__('json'),
            're': __import__('re'),
            'time': __import__('time'),
            'datetime': __import__('datetime'),
            # Only allow these builtins!
            '__builtins__': {k: getattr(builtins, k) for k in self.allowed_builtins}
        }

        # Step 3: Set up undo step (push undo for safety)
        bpy.ops.ed.undo_push(message="AI Code Execution")

        # Step 4: Capture stdout (for print output)
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            exec(code, exec_globals)
            output = captured_output.getvalue()
            bpy.context.view_layer.update()
            return True, "Code executed successfully.", output
        except Exception as ex:
            tb = traceback.format_exc()
            # Optionally, auto-undo on error
            bpy.ops.ed.undo()
            return False, f"Error during code execution: {ex}\n\n{tb}", captured_output.getvalue()
        finally:
            sys.stdout = old_stdout

