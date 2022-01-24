"""templite测试用例"""

import re
import unittest
from templite import TempliteSyntaxError, Templite


class AnyOldObject(object):
    """简单的测试对象
    在构造函数中使用关键字参数来设置对象属性
    """
    def __init__(self, **attrs):
        for n, v in attrs.items():
            setattr(self, n, v)

class TempliteTest(unittest.TestCase):
    """Templite测试用例"""
    def try_render(self, text, ctx=None, result=None):
        """通过 `ctx` 渲染 `text`，最好是包含 `result` 。
        result默认是None，因此我们可以减少调用时间，
        不进行结果比较
        """
        actual = Templite(text).render(ctx or {})
        if result:
            self.assertEqual(actual, result)

    def assertSynErr(self, msg):
        pat = "^" + re.escape(msg) + "$"
        return self.assertRaisesRegex(TempliteSyntaxError, pat)

    def test_passthrough(self):
        # 没有参数的字符串直接通过，不进行任何修改
        self.assertEqual(Templite("Hello").render(), "Hello")
        self.assertEqual(
            Templite("Hello, 20% fun time!").render(),
            "Hello, 20% fun time!"
        )

    def test_variables(self):
        # 变量使用 {{var}} 语法
        self.try_render("Hello, {{name}}!", {'name': 'Ned'}, "Hello, Ned!")

    def test_undefined_variables(self):
        # 使用未定位名称
        with self.assertRaises(Exception):
            self.try_render("Hi, {{name}}!")

    def test_pipes(self):
        # 变量会被pipe过滤
        data = {
            'name': 'Ned',
            'upper': lambda x: x.upper(),
            'second': lambda x: x[1]
        }
        self.try_render("Hello, {{name|upper}}!", data, "Hello, NED!")

        self.try_render("Hello, {{name|upper|second}}!", data, "Hello, E!")

    def test_reusability(self):
        # 一个 templite 可以被多个 data 使用
        globs = {
            'upper': lambda x: x.upper(),
            'punct': '!'
        }
        template = Templite("This is {{name|upper}}{{punct}}", globs)
        self.assertEqual(template.render({'name':'Ned'}), "This is NED!")
        self.assertEqual(template.render({'name':'Ben'}), "This is BEN!")

    def test_attribute(self):
        # 变量的属性可以通过点获取
        obj = AnyOldObject(a="Ay")
        self.try_render("{{obj.a}}", locals(), 'Ay')

        obj2 = AnyOldObject(obj=obj, b='Bee')
        self.try_render("{{obj2.obj.a}} {{obj2.b}}", locals(), "Ay Bee")

    def test_member_function(self):
        # 变量的成员函数可以使用，只要它们是空的
        class WithMemberFns(AnyOldObject):
            """用于尝试成员函数访问的类"""
            def ditto(self):
                """返回两次 .txt 属性"""
                return self.txt + self.txt
        obj = WithMemberFns(txt="Once")
        self.try_render("{{obj.ditto}}", locals(), "OnceOnce")

    def test_item_access(self):
        # 变量的项可以使用
        d = {'a': 17, 'b': 23}
        self.try_render("{{d.a}} < {{d.b}}", locals(), "17 < 23")

    def test_loops(self):
        # 循环
        nums = [1, 2, 3, 4]
        self.try_render(
            "Look: {% for n in nums %}{{n}}, {% endfor %}done.",
            locals(),
            "Look: 1, 2, 3, 4, done."
        )
        # 循环可以过滤
        def rev(l):
            """返回 `l` 的反转"""
            l = l[:]
            l.reverse()
            return l

        self.try_render(
            "Look: {% for n in nums|rev %}{{n}}, {% endfor %}done.",
            locals(),
            "Look: 4, 3, 2, 1, done."
        )
    def test_empty_loops(self):
        self.try_render(
            "Empty: {% for n in nums %}{{n}}, {% endfor %}done.",
            {'nums': []},
            "Empty: done."
        )

    def test_multiline_loops(self):
        self.try_render(
            "Look: \n{% for n in nums %}\n{{n}}, \n{% endfor %}done.",
            {'nums': [1, 2, 3]},
            "Look: \n\n1, \n\n2, \n\n3, \ndone."
        )

    def test_multiple_loops(self):
        self.try_render(
            "{% for n in nums %}{{n}}{% endfor %} and "
                        "{% for n in nums %}{{n}}{% endfor %}",
            {'nums': [1, 2, 3]},
            "123 and 123"
        )

    def test_comments(self):
        # 单行注释
        self.try_render(
            "Hello, {# Name goes here: #}{{name}}!",
            {'name':'Ned'}, "Hello, Ned!"
        )
        # 多行注释
        self.try_render(
            "Hello, {# Name\ngoes\nhere: #}{{name}}!",
            {'name':'Ned'}, "Hello, Ned!"
        )

    def test_if(self):
        self.try_render(
            "Hi, {% if ned %}NED{% endif %}{% if ben %}BEN{% endif %}!",
            {'ned': 1, 'ben': 0},
            "Hi, NED!"
        )
        self.try_render(
            "Hi, {% if ned %}NED{% endif %}{% if ben %}BEN{% endif %}!",
            {'ned': 0, 'ben': 1},
            "Hi, BEN!"
        )
        self.try_render(
            "Hi, {% if ned %}NED{% endif %}{% if ben %}BEN{% endif %}!",
            {'ned': 0, 'ben': 0},
            "Hi, !"
        )
        self.try_render(
            "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
            {'ned': 1, 'ben': 0},
            "Hi, NED!"
        )
        self.try_render(
            "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
            {'ned': 1, 'ben': 1},
            "Hi, NEDBEN!"
        )

    def test_complex_if(self):
        class Complex(AnyOldObject):
            """尝试负责数据访问的类"""
            def getit(self):
                """返回it"""
                return self.it
        obj = Complex(it={'x':'Hello', 'y':0})
        self.try_render(
            "@"
            "{% if obj.getit.x %}X{% endif %}"
            "{% if obj.getit.y %}Y{% endif %}"
            "{% if obj.getit.y|str %}S{% endif %}"
            "!",
            {'obj': obj, 'str': str},
            "@XS!"
        )

    def test_loop_if(self):
        self.try_render(
            "@{% for n in nums %}{% if n %}Z{% endif %}{{n}}{% endfor %}!",
            {'nums': [0,1,2]},
            "@0Z1Z2!"
            )
        self.try_render(
            "X{%if nums%}@{% for n in nums %}{{n}}{% endfor %}{%endif%}!",
            {'nums': [0,1,2]},
            "X@012!"
            )
        self.try_render(
            "X{%if nums%}@{% for n in nums %}{{n}}{% endfor %}{%endif%}!",
            {'nums': []},
            "X!"
            )

    def test_nested_loops(self):
        self.try_render(
            "@"
            "{% for n in nums %}"
                "{% for a in abc %}{{a}}{{n}}{% endfor %}"
            "{% endfor %}"
            "!",
            {'nums': [0,1,2], 'abc': ['a', 'b', 'c']},
            "@a0b0c0a1b1c1a2b2c2!"
            )

    def test_exception_during_evaluation(self):
        # TypeError: Couldn't evaluate {{ foo.bar.baz }}:
        # 'NoneType' object is unsubscriptable
        with self.assertRaises(TypeError):
            self.try_render(
                "Hey {{foo.bar.baz}} there", {'foo': None}, "Hey ??? there"
            )

    def test_bad_names(self):
        with self.assertSynErr("Not a valid name: 'var%&!@'"):
            self.try_render("Wat: {{ var%&!@ }}")
        with self.assertSynErr("Not a valid name: 'filter%&!@'"):
            self.try_render("Wat: {{ foo|filter%&!@ }}")
        with self.assertSynErr("Not a valid name: '@'"):
            self.try_render("Wat: {% for @ in x %}{% endfor %}")

    def test_malformed_if(self):
        with self.assertSynErr("Don't understand if: '{% if %}'"):
            self.try_render("Buh? {% if %}hi!{% endif %}")
        with self.assertSynErr("Don't understand if: '{% if this or that %}'"):
            self.try_render("Buh? {% if this or that %}hi!{% endif %}")

    def test_malformed_for(self):
        with self.assertSynErr("Don't understand for: '{% for %}'"):
            self.try_render("Weird: {% for %}loop{% endfor %}")
        with self.assertSynErr("Don't understand for: '{% for x from y %}'"):
            self.try_render("Weird: {% for x from y %}loop{% endfor %}")
        with self.assertSynErr("Don't understand for: '{% for x, y in z %}'"):
            self.try_render("Weird: {% for x, y in z %}loop{% endfor %}")

    def test_bad_nesting(self):
        with self.assertSynErr("Unmatched action tag: 'if'"):
            self.try_render("{% if x %}X")
        with self.assertSynErr("Mismatched end tag: 'for'"):
            self.try_render("{% if x %}X{% endfor %}")
        with self.assertSynErr("Too many ends: '{% endif %}'"):
            self.try_render("{% if x %}{% endif %}{% endif %}")

    def test_malformed_end(self):
        with self.assertSynErr("Don't understand end: '{% end if %}'"):
            self.try_render("{% if x %}X{% end if %}")
        with self.assertSynErr("Don't understand end: '{% endif now %}'"):
            self.try_render("{% if x %}X{% endif now %}")



