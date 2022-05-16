"""Byterun 的函数场景测试"""

import vmtest


class TestFunctions(vmtest.VmTestCase):
    def test_functions(self):
        self.assert_ok("""\
            def fn(a, b=17, c="Hello", d=[]):
                d.append(99)
                print(a, b, c, d)
            fn(1)
            fn(2, 3)
            # fn(3, c="Bye") # not supporting KWargs
            # fn(4, d=["What?"])
            fn(5, "b", "c")
            """)

    def test_recursion(self):
        self.assert_ok("""\
            def fact(n):
                if n <= 1:
                    return 1
                else:
                    return n * fact(n-1)
            f6 = fact(6)
            print(f6)
            assert f6 == 720
            """)

    # def test_calling_functions_with_args_kwargs(self):
    #      """ KW args unsupported"""
    #     self.assert_ok("""\
    #         def fn(a, b=17, c="Hello", d=[]):
    #             d.append(99)
    #             print(a, b, c, d)
    #         fn(6, *[77, 88])
    #         fn(**{'c': 23, 'a': 7})
    #         fn(6, *[77], **{'c': 23, 'd': [123]})
    #         """)

    def test_defining_functions_with_args_kwargs(self):
        self.assert_ok("""\
            def fn(*args):
                print("args is %r" % (args,))
            fn(1, 2)
            """)
        # self.assert_ok("""\
        #     def fn(**kwargs):
        #         print("kwargs is %r" % (kwargs,))
        #     fn(red=True, blue=False)
        #     """)
        # self.assert_ok("""\
        #     def fn(*args, **kwargs):
        #         print("args is %r" % (args,))
        #         print("kwargs is %r" % (kwargs,))
        #     fn(1, 2, red=True, blue=False)
        #     """)
        # self.assert_ok("""\
        #     def fn(x, y, *args, **kwargs):
        #         print("x is %r, y is %r" % (x, y))
        #         print("args is %r" % (args,))
        #         print("kwargs is %r" % (kwargs,))
        #     fn('a', 'b', 1, 2, red=True, blue=False)
        #     """)

    def test_defining_functions_with_empty_args_kwargs(self):
        self.assert_ok("""\
            def fn(*args):
                print("args is %r" % (args,))
            fn()
            """)
        self.assert_ok("""\
            def fn(**kwargs):
                print("kwargs is %r" % (kwargs,))
            fn()
            """)
        self.assert_ok("""\
            def fn(*args, **kwargs):
                print("args is %r, kwargs is %r" % (args, kwargs))
            fn()
            """)

    def test_partial(self):
        self.assert_ok("""\
            from _functools import partial

            def f(a,b):
                return a-b

            f7 = partial(f, 7)
            four = f7(3)
            assert four == 4
            """)