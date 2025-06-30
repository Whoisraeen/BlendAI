import bpy
import sys
import traceback
import builtins
import ast
import signal
import threading
from io import StringIO
from contextlib import contextmanager

class CodeExecutor:
    def __init__(self):
        # Only allow these modules and builtins!
        # To add more modules safely:
        # 1. Ensure the module doesn't provide file system access
        # 2. Ensure it doesn't allow arbitrary code execution
        # 3. Test thoroughly in a safe environment first
        # 4. Add to this set and update documentation
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
        # Execution timeout in seconds (helps prevent infinite loops)
        self.execution_timeout = 30

    def validate_code(self, code):
        """
        Use AST parsing to detect dangerous statements (import, exec, eval, etc).
        Enhanced validation with additional security checks.
        Returns (is_safe: bool, message: str)
        """
        try:
            tree = ast.parse(code, mode='exec')
        except Exception as ex:
            return False, f"Code could not be parsed: {ex}"

        # Additional dangerous patterns to check
        dangerous_names = {
            'exec', 'eval', 'compile', 'open', 'input', 'raw_input', '__import__',
            'globals', 'locals', 'vars', 'dir', 'delattr', 'setattr'
        }
        
        # Check for potential obfuscation patterns
        suspicious_patterns = {
            'getattr', 'hasattr', 'setattr', 'delattr'  # Could be used to access dangerous attributes
        }

        for node in ast.walk(tree):
            # Block all import statements
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return False, "Imports are not allowed!"
            
            # Block dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in dangerous_names:
                        return False, f"Usage of dangerous function '{node.func.id}' detected!"
                    # Warn about suspicious patterns that could be used for obfuscation
                    if node.func.id in suspicious_patterns:
                        # Allow basic usage but block if used with string literals that look suspicious
                        if isinstance(node.args[0] if node.args else None, ast.Constant):
                            if isinstance(node.args[0].value, str) and node.args[0].value.startswith('__'):
                                return False, f"Suspicious usage of '{node.func.id}' with dunder attribute detected!"
            
            # Block access to dunder attributes
            if isinstance(node, ast.Attribute):
                if node.attr.startswith("__"):
                    return False, f"Access to dunder attribute '{node.attr}' is not allowed!"
            
            # Block global/locals manipulation
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                return False, "Global and nonlocal declarations are not allowed!"
            
            # Block while True loops (common infinite loop pattern)
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    return False, "Infinite 'while True' loops are not allowed for safety!"

        # All checks passed
        return True, "Code appears safe"

    @contextmanager
    def timeout_context(self, timeout_seconds):
        """Context manager for execution timeout (basic implementation)"""
        def timeout_handler():
            raise TimeoutError(f"Code execution timed out after {timeout_seconds} seconds")
        
        timer = threading.Timer(timeout_seconds, timeout_handler)
        timer.start()
        try:
            yield
        finally:
            timer.cancel()
    
    def safe_object_access(self, obj, attr_name, default=None):
        """Safely access object attributes with proper error handling"""
        try:
            if hasattr(obj, attr_name):
                return getattr(obj, attr_name, default)
            return default
        except:
            return default
    
    def execute_code(self, code):
        """
        Executes validated code in a restricted environment with enhanced safety.
        Returns: (success: bool, message: str, output: str)
        """
        # Step 1: Validate code
        is_safe, message = self.validate_code(code)
        if not is_safe:
            return False, message, ""

        # Step 2: Prepare restricted globals with safe object access helper
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
            # Helper function for safe object access
            'safe_access': self.safe_object_access,
            # Only allow these builtins!
            '__builtins__': {k: getattr(builtins, k) for k in self.allowed_builtins}
        }

        # Step 3: Set up undo step (push undo for safety)
        bpy.ops.ed.undo_push(message="AI Code Execution")

        # Step 4: Capture stdout (for print output)
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            # Step 5: Execute with timeout protection
            with self.timeout_context(self.execution_timeout):
                exec(code, exec_globals)
            
            output = captured_output.getvalue()
            bpy.context.view_layer.update()
            return True, "Code executed successfully.", output
            
        except TimeoutError as ex:
            # Handle timeout specifically
            bpy.ops.ed.undo()
            return False, f"Code execution timed out: {ex}", captured_output.getvalue()
        except Exception as ex:
            tb = traceback.format_exc()
            # Auto-undo on error for safety
            bpy.ops.ed.undo()
            
            # Enhanced error message for common issues
            error_msg = str(ex)
            if "has no attribute 'data'" in error_msg:
                error_msg += "\nTip: Check if object has data before accessing (e.g., if obj.data: ...)"
            elif "'NoneType'" in error_msg:
                error_msg += "\nTip: Check for None values before accessing attributes"
            
            return False, f"Error during code execution: {error_msg}\n\n{tb}", captured_output.getvalue()
        finally:
            sys.stdout = old_stdout


# DOCUMENTATION: How to Safely Add More Allowed Modules
# =====================================================
# 
# To expand the allowed modules for AI-generated code execution:
# 
# 1. Add the module name to the exec_globals dictionary in execute_code():
#    'new_module': __import__('new_module'),
# 
# 2. Consider security implications:
#    - Avoid modules that provide file system access (os, subprocess, etc.)
#    - Avoid modules that can execute arbitrary code (importlib, etc.)
#    - Avoid network-related modules (urllib, requests, etc.)
# 
# 3. Safe modules to consider adding:
#    - 'numpy': For advanced mathematical operations
#    - 'collections': For specialized data structures
#    - 'itertools': For advanced iteration tools
#    - 'operator': For functional programming operations
# 
# 4. Test thoroughly:
#    - Ensure the module doesn't introduce security vulnerabilities
#    - Verify it works correctly within Blender's Python environment
#    - Check for any conflicts with existing Blender functionality
# 
# Example of adding numpy (if available):
# try:
#     import numpy
#     exec_globals['numpy'] = numpy
# except ImportError:
#     pass  # numpy not available, skip
# 
# Remember: The goal is to provide useful functionality while maintaining
# security and preventing potentially harmful code execution.

