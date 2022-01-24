"""一个简单的 Python 模板渲染器，用于 Django 语法的 nano 子级"""

import re

class TempliteSyntaxError(ValueError):
    """当模板有语法错误时引发"""
    pass

class CodeBuilder(object):
    """方便地构建源代码"""

    def __init__(self, indent=0):
        self.code = []
        self.indent_level = indent

    def __str__(self):
        return "".join(str(c) for c in self.code)

    def add_line(self, line):
        """在 code 中添加一行源代码。
        缩进和换行会自动添加，无需提供。
        """
        self.code.extend([" " * self.indent_level, line, "\n"])

    def add_section(self):
        """添加一个块，一个子 CodeBuilder"""
        section = CodeBuilder(self.indent_level)
        self.code.append(section)
        return section
    
    INDENT_STEP = 4 # PEP8 规范

    def indent(self):
        """为后续行增加一个缩进"""
        self.indent_level += self.INDENT_STEP

    def dedent(self):
        """为后续行减少一个缩进"""
        self.indent_level -= self.INDENT_STEP

    def get_globals(self):
        """执行代码，并返回它定义的全局变量字典"""
        # 检查调用者是否真的完成了所有块。
        assert self.indent_level == 0
        # 获取 Python 源作为一个字符串
        python_source = str(self)
        # 执行 Python源，定义全局变量并返回它们
        global_namespace = {}
        exec(python_source, global_namespace)
        return global_namespace

class Templite(object):
    def __init__(self, text, *contexts):
        """一个简单的 Python 模板渲染器，用于 Django 语法的 nano 子级。
        支持扩展变量访问结构::
            {{var.modifer.modifier|filter|filter}}
        循环::
            {% for var in list %}...{% endfor %}
        条件语句::
            {% if var %}...{% endif %}
        注释在井号里面::
            {# This will be ignored #}
        用模板本文构建 Templite， 然后对字典上下文使用 `render` 来创建
        最终的字符串::
            templite = Templite('''
                <h1>Hello {{name|upper}}!</h1>
                {% for topic in topics %}
                    <p>You are interested in {{topic}}.</p>
                {% endif %}
                ''',
                {'upper': str.upper},
            )
            text = templite.render({
                'name': "Ned",
                'topics': ['Python', 'Geometry', 'Juggling'],
            })
        """
        self.context = {}
        for context in contexts:
            self.context.update(context)

        self.all_vars = set()
        self.loop_vars = set()

        code = CodeBuilder()

        code.add_line("def render_function(context, do_dots):")
        code.indent()
        vars_code = code.add_section()
        code.add_line("result = []")
        code.add_line("append_result = result.append")
        code.add_line("extend_result = result.extend")
        code.add_line("to_str = str")

        buffered = []

        def flush_output():
            """将 `buffered` 输出到代码生成器"""
            if len(buffered) == 1:
                code.add_line("append_result(%s)" % buffered[0])
            elif len(buffered) > 1:
                code.add_line("extend_result([%s])" % ", ".join(buffered))
            del buffered[:]
        
        ops_stack = []
        tokens = re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)

        for token in tokens:
            if token.startswith('{#'):
                # 注释：忽略并继续
                continue
            elif token.startswith('{{'):
                # 要计算的表达式
                expr = self._expr_code(token[2:-2].strip())
                buffered.append("to_str(%s)" % expr)
            elif token.startswith('{%'):
                # 活动标签，拆分成 words 并进一步解析
                flush_output()
                words = token[2:-2].strip().split()
                if words[0] == 'if':                   
                    # if语句，计算表达式以确定if
                    if len(words) != 2:
                        self._syntax_error("Don't understand if", token)
                    ops_stack.append('if')
                    code.add_line("if %s:" % self._expr_code(words[1]))
                    code.indent()
                elif words[0] == 'for':
                    # 循环，迭代表达式结果
                    if len(words) != 4 or words[2] != 'in':
                        self._syntax_error("Don't understand for", token)
                    ops_stack.append('for')
                    self._variable(words[1], self.loop_vars)
                    code.add_line(
                        "for c_%s in %s:" % (
                            words[1],
                            self._expr_code(words[3])
                        )
                    )
                    code.indent()
                elif words[0].startswith('end'):
                    # 结束上一个，弹出 ops
                    if len(words) != 1:
                        self._syntax_error("Don't understand end", token)
                    end_what = words[0][3:]
                    if not ops_stack:
                        self._syntax_error("Too many ends", token)
                    start_what = ops_stack.pop()
                    if start_what != end_what:
                        self._syntax_error("Mismatched end tag", end_what)
                    code.dedent()
                else:
                    self._syntax_error("Don't understand tag", words[0])
            else:
                # 文字内容，如果不是空的就输出
                if token:
                    buffered.append(repr(token))

        if ops_stack:
            self._syntax_error("Unmatched action tag", ops_stack[-1])

        flush_output()

        for var_name in self.all_vars - self.loop_vars:
            vars_code.add_line("c_%s = context[%r]" % (var_name, var_name))

        code.add_line("return ''.join(result)")
        code.dedent()
        self._render_function = code.get_globals()['render_function']

    def _expr_code(self, expr):
        """为 `expr` 生成 Python 表达式"""
        if "|" in expr:
            pipes = expr.split("|")
            code =self._expr_code(pipes[0])
            for func in pipes[1:]:
                self._variable(func, self.all_vars)
                code = "c_%s(%s)" % (func, code)
        elif "." in expr:
            dots = expr.split(".")
            code = self._expr_code(dots[0])
            args = ", ".join(repr(d) for d in dots[1:])
            code = "do_dots(%s, %s)" % (code, args)
        else:
            self._variable(expr, self.all_vars)
            code = "c_%s" % expr
        return code

    def _syntax_error(self, msg, thing):
        """使用 `msg` 引发语法错误，并显示 `thing`"""
        raise TempliteSyntaxError("%s: %r" % (msg, thing))

    def _variable(self, name, vars_set):
        """跟踪 `name` ，被用作变量
        将 name 添加到 `vars_set`，它是变量名的集合。
        如果 `name` 不合法引发异常
        """
        if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", name):
            self._syntax_error("Not a valid name", name)
        vars_set.add(name)

    def render(self, context=None):
        """通过应用 `context`渲染模板
        `context` 是用来渲染的值的字典
        """
        # 生成完整的context
        render_context = dict(self.context)
        if context:
            render_context.update(context)
        return self._render_function(render_context, self._do_dots)

    def _do_dots(self, value, *dots):
        """运行时计算点表达式"""
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if callable(value):
                value = value()
        return value

