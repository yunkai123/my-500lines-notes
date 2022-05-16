""" byterun 的测试工具类 """

import dis
import io
import sys
import textwrap
import types
import unittest

from byterun.pyvm2 import VirtualMachine, VirtualMachineError

# 如果需要在测试中运行调试器，请将此设置为false。
CAPTURE_STOUT = ('-s' not in sys.argv)
# 将此设置为false以查看 pyvm2 内部故障的异常堆栈。
CAPTURE_EXCEPTION = 1

def dis_code(code):
    """ 返汇编 `code` 及其引用的所有代码"""
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            dis_code(const)

    print("")
    print(code)
    dis.dis(code)

class VmTestCase(unittest.TestCase):
    
    def assert_ok(self, code, raises=None):
        """在我们的 VM 和真实的 Python 中运行`code`：它们的行为相同。"""
        code = textwrap.dedent(code)
        code = compile(code, "<%s>" % self.id(), "exec", 0, 1)

        # 打印反汇编，以便在测试失败时查看。
        dis_code(code)

        real_stdout = sys.stdout

        # 通过我们的 VM 运行代码

        vm_stdout = io.StringIO()
        if CAPTURE_STOUT:
            sys.stdout = vm_stdout
        vm = VirtualMachine()

        vm_value = vm_exc = None
        try:
            vm_value = vm.run_code(code)
        except VirtualMachineError:
            # 如果 VM 代码引发错误，显示它。
            raise
        except AssertionError:
            # 如果测试代码未能通过断言，显示它。
            raise
        except Exception as e:
            # 否则，请保留异常以供以后比较。
            if not CAPTURE_EXCEPTION:
                raise
            vm_exc = e
        finally:
            real_stdout.write("-- stdout ----------\n")
            real_stdout.write(vm_stdout.getvalue())

        # 通过真正的 Python 解释器运行代码，以进行比较。

        py_stdout = io.StringIO()
        sys.stdout = py_stdout

        py_value = py_exc = None
        globs = {}
        try:
            py_value = eval(code, globs, globs)
        except AssertionError:
            raise
        except Exception as e:
            py_exc = e

        sys.stdout = real_stdout

        self.assert_same_exception(vm_exc, py_exc)
        self.assertEqual(vm_stdout.getvalue(), py_stdout.getvalue())
        self.assertEqual(vm_value, py_value)
        if raises:
            self.assertIsInstance(vm_exc, raises)
        else:
            self.assertIsNone(vm_exc)

    def assert_same_exception(self, e1, e2):
        """异常不实现 __eq__，我们自行检查"""
        self.assertEqual(str(e1), str(e2))
        self.assertIs(type(e1), type(e2))





