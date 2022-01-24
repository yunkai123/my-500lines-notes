# 模板引擎

## 作者

Ned Batchelder，Ned Batchelder 是一名有着长期职业生涯的软件工程师，目前在 edX 工作，通过构建开放源码软件来进行教育事业。他是 coverage.py 的维护者，Boston Python 的组织者，并在许多 PyCons 上演讲。他的博客是 http://nedbatchelder.com。他曾经在白宫吃过晚饭。

## 介绍

大多数程序包含大量的逻辑和少量的文本数据，编程语言被设计成适合这种编程。但是有些编程任务只涉及少量逻辑和大量文本数据。我们希望有一个工具解决这些大量文本的任务。模板引擎就是这样一种工具。在本文中，我们构建一个简单的模板引擎。

包含大量文本的最常见例子是 Web 应用程序。Web 应用程序的一个重要阶段是生成浏览器使用的 HTML。 HTML 页面很少是完全静态的：它们包含少量的动态数据，比如用户名或者大量的动态数据：产品列表、朋友的新消息等等。

同时，每个 HTML 页面还包含大量的静态文本。这些页面很大，文本中包含成千上万字节。Web 应用程序开发人员面临着一个重要问题：如何优雅地生成一个静态和动态数据混合的大字符串？另外，静态文本实际上是 HTML 标记语言，由团队的另一个成员前端设计师采用他们最熟悉的方式编写。

为了便于说明，让我们假设我们要制作如下的简单 HTML：

```html
<p>Welcome, Charlie!</p>
<p>Products:</p>
<ul>
    <li>Apple: $1.00</li>
    <li>Fig: $1.50</li>
    <li>Pomegranate: $3.25</li>
</ul>
```

在这里，用户名是动态的，产品的名称和价格也是动态的。甚至产品的数量也不固定：在不同时间可能会显示不同数量的产品。

生成这个 HTML 的一种方法是在代码中使用字符串常量，并将它们连接在一起以生成页面。动态数据会被字符串常量替换。我们的一些动态数据是重复的，比如我们的产品列表。这意味着我们将有大量重复的 HTML，因此我们将它们单独处理再与页面的其余部分结合。

上述生成的页面的方式如下所示：

```py
# 页面 HTML
PAGE_HTML = """
<p>Welcome, {name}!</p>
<p>Products:</p>
<ul>
{products}
</ul>
"""

# 每个产品展示的 HTML 
PRODUCT_HTML = "<li>{prodname}: {price}</li>\n"

def make_page(username, products):
    product_html = ""
    for prodname, price in products:
        product_html += PRODUCT_HTML.format(
            prodname=prodname, price=format_price(price))
    html = PAGE_HTML.format(name=username, products=product_html)
    return html
```

这种方式可以工作，但看起来比较凌乱。HTML 包含在我们的应用程序代码中的字符串常量中。页面的逻辑很不清晰，因为静态文本被分成了几个独立的部分。Python 代码中丢失了数据格式的详细信息。为了修改 HTML 页面，我们的前端设计师需要学会编辑 Python 代码。想象一下，如果页面复杂十倍或百倍，代码会是什么样子，它很快就会变得不可操作。

## 模板

生成 HTML 页面更好的方式是使用模板。HTML 页面作为模板编写，这意味着文件主要是静态 HTML，其中使用特殊的符号嵌入动态部分。我们上面的示例页面作为模板如下所示：

```html
<p>Welcome, {{user_name}}!</p>
<p>Products:</p>
<ul>
{% for product in product_list %}
    <li>{{ product.name }}:
        {{ product.price|format_price }}</li>
{% endfor %}
</ul>
```

这里的重点是 HTML 文本，其中嵌入了逻辑。将这种以文档为中心的方法与上面的以逻辑为中心的代码进行对比。我们之前的程序主要是 Python 代码，在 Python 逻辑中嵌入了HTML。在这里我们的程序主要是静态 HTML 标记。

模板中使用的以静态为主的样式与大多数编程语言的工作方式相反。例如，对于 Python，大多数源文件都是可执行代码，如果需要静态文本，可以将其嵌入到字符串中：

```py
def hello():
    print("Hello, world!")

hello()
```

当 Python 读取这个源文件时，它将 `def hello():` 之类的文本解释为要执行的指令。而在 `print("Hello, world!")` 中双引号表明其中的文本只是字面上的意思。大多数编程语言都是这样工作的：以动态为主，指令中嵌入了一些静态部分，静态部分用双引号标记。

模板语言与此相反：模板文件主要是静态文本，用特殊的符号表示可执行的动态部分。

```html
<p>Welcome, {{user_name}}!</p>
```

在这里，文本将按字面意思显示在生成的 HTML 页面中，直到 {{ 表示切换到动态模式，其中 `user_name` 变量将在输出中被替换。

字符串格式化函数，如 Python 的 `"foo = {foo}!".format(foo=17)` 是从字符串文本和要插入的数据创建文本的一个示例。模板扩展了这一思想，包括条件句和循环等结构，区别只是程度不同。

这些文件之所以称为模板是因为它们被用来生成许多结构相似但细节不同的页面。

为了在我们的程序中使用 HTML 模板，我们需要一个*模板引擎*：一个使用静态模板描述页面结构和静态内容的函数，以及一个提供动态数据以插入模板的动态*上下文*。模板引擎将模板和上下文结合起来生成一个完整的 HTML 字符串。模板引擎的工作是解释模板，用真实数据替换其中的动态片段。

顺便说一句，模板引擎中并不仅为 HTML，它可以用来生成任何文本结果。例如，它们也用于生成纯文本电子邮件。但是它们一般用于 HTML，并且具有某些 HTML 特有的特性，比如转义，这使得在 HTML 中插入值而不必担心其是否为特殊字符。

## 支持的语法

模板引擎支持的语法各不相同。我们的模板语法基于 Django，一个流行的 Web 框架。由于我们是用 Python 实现引擎的，因此我们的语法中会出现一些 Python 概念。我们已经在本文顶部的示例中看到了一些相关语法，这是我们将要实现的语法的一部分。

上下文中的数据使用双大括号插入：

```
<p>Welcome, {{user_name}}!</p>
```

模板可用的数据在渲染模板时通过上下文提供，稍后再谈。

模板引擎通常使用简化和宽松的语法来访问数据中的元素。在 Python 中，这些表达式都有不同的效果： 

```py
dict["key"]
obj.attr
obj.method()
```

在我们的模板语法中，所有这些操作都用一个点表示：

```
dict.key
obj.attr
obj.method
```

点将访问对象属性或字典的值，并且如果结果值是可调用的方法，则会自动调用它。这语法与 Python 不同，但这样可以简化模板语法：

```html
<p>The price is: {{product.price}}, with a {{product.discount}}% discount.</p>
```

你可以使用被称作*过滤器*的函数来修改值。通过管道字符（竖线）可以调用过滤器：

```html
<p>Short name: {{story.subject|slugify|lower}}</p>
```

创建页面有时需要一些条件决策，因此可以使用条件：

```html
{% if user.is_logged_in %}
    <p>Welcome, {{ user.name }}!</p>
{% endif %}
```

循环允许我们在页面中包含数据集合：

```html
<p>Products:</p>
<ul>
{% for product in product_list %}
    <li>{{ product.name }}: {{ product.price|format_price }}</li>
{% endfor %}
</ul>
```

与其他编程语言一样，模板中可以嵌套条件语句和循环来构建复杂的逻辑结构。

最后，为了可以为模板添加注释，使用大括号井号包含注释：

```
{# This is the best template ever! #}
```

## 实现方法

大体来说，模板引擎将有两个主要阶段：解析模板然后渲染模板。

渲染模板具体包括：

- 管理数据源和动态上下文
- 执行逻辑元素
- 实现点访问和过滤器

从解析阶段传递到渲染阶段什么内容是关键。解析产生什么用来渲染？有两个主要选项；使用其他语言实现中的术语，我们称之为*解释*和*编译*。

在解释模型中，解析生成表示模板结构的数据结构。渲染阶段遍历数据结构，根据找到的指令组合装配结果文本。作为一个真实的例子，Django 模板引擎就是使用这种方法。

在编译模型中，解析生成某种形式的可以直接执行的代码。渲染阶段执行该代码并产生结果。Jinja2 和 Mako 是两个使用编译方法的模板引擎的例子。

我们的引擎实现使用编译模型：我们将模板编译成 Python 代码。运行时，Python 代码将结果组装起来。

这里描述的模板引擎最初是作为 coverage.py 的一部分，用以生成 HTML 报告。在 coverage.py，只有很少几个模板，它们被反复使用生成许多文件。总的来说，如果将模板编译成 Python 代码，程序会运行得更快，因为即使编译过程稍微复杂一些，它也只需运行一次，而编译后的代码要运行很多次，比多次解释数据结构快很多。

将模板编译成 Python 有点复杂，但并不像你想象的那么困难。此外，正如任何开发人员都可以告诉你的，编写能够编写程序的程序比编写程序更有趣！

我们的模板编译器是一种称为代码生成的通用技术的小例子。代码生成是许多强大而灵活的工具的基础，包括编程语言编译器。代码生成可能学起来很复杂，但它是一种值得掌握的技术。

如果每个模板只使用几次，那么应用程序可能更喜欢解释方法。从长远来看，编译成 Python 并没有多少优势，稍简单的解释过程可能会在整体上表现更好。

## 编译为 Python

在讨论模板引擎的代码之前，让我们先看看它生成的代码。解析阶段将模板转换为 Python 函数。这是我们的小模板：

```html
<p>Welcome, {{user_name}}!</p>
<p>Products:</p>
<ul>
{% for product in product_list %}
    <li>{{ product.name }}:
        {{ product.price|format_price }}</li>
{% endfor %}
</ul>
```

我们的引擎将把这个模板编译成 Python 代码。生成的 Python 代码看起来有些不寻常，这是因为我们选使用了一些快捷方式来生成速度稍快的代码。下面是Python 代码，为了可读性进行了重新格式化：

```py
def render_function(context, do_dots):
    c_user_name = context['user_name']
    c_product_list = context['product_list']
    c_format_price = context['format_price']

    result = []
    append_result = result.append
    extend_result = result.extend
    to_str = str

    extend_result([
        '<p>Welcome, ',
        to_str(c_user_name),
        '!</p>\n<p>Products:</p>\n<ul>\n'
    ])
    for c_product in c_product_list:
        extend_result([
            '\n    <li>',
            to_str(do_dots(c_product, 'name')),
            ':\n        ',
            to_str(c_format_price(do_dots(c_product, 'price'))),
            '</li>\n'
        ])
    append_result('\n</ul>\n')
    return ''.join(result)
```

每个模板都转换为一个 `render_function` 函数，该函数参数为 context 数据字典。函数体首先将 context 中的数据转换为局部变量，这样可以提高速度。所有的 context 中的数据都放入以 `c_` 为前缀的局部变量中，这样我们就可以不必担心和其它局部变量产生冲突。

模板的结果将是一个字符串。将多个部件构建成字符串的最快方法是创建一个字符串列表，然后将它们连接在一起。`result` 是一个字符串列表。因为我们要向这个列表中添加字符串，所以我们将它的 `append` 和 `extend` 方法赋给局部变量 `result_append` 和 `result_extend`。我们创建的最后一个局部变量是内建方法 `str` 的快捷方式 `to_str` 。

这些快捷方式并不寻常。让我们更仔细地看一下。在 Python 中，一个方法被对象调用，如 `result.append("hello")`，分两步执行。首先，从 `result` 对象获取 `append` 属性：`result.append`。然后，调用获取的属性值作为函数，并将参数 `"hello"` 传递给它。虽然我们习惯于看到这些步骤同时执行，但它们实际上是分开的。如果保存了第一步的结果，那么可以对保存的结果直接执行第二步。因此，下面两个 Python 代码段做了同样的事情：

```py
# 我们习惯使用的方式:
result.append("hello")

# 下面的效果相同:
append_result = result.append
append_result("hello")
```

在模板引擎代码中，我们以这种方式将其分开，这样我们不管执行第二步多少次，都只执行第一步一次。这节省了我们少量的时间，因为这样避免了花时间查找 `append` 属性。

这是一个微优化的例子：一种不同寻常的编码技术使我们的速度获得微小的提升。微优化可能不那么可读，或者令人感到困惑，因此它们仅适用于性能瓶颈已验证的代码。开发人员对微优化的合理性存在分歧，有些初学者会过度使用它。这里的优化只是在性能测试表明它们提高了性能之后才添加的，即使只是稍微有一点提高。微优化有时具有指导意义，因为它们使用了 Python 的一些不常用特性，但不要在你自己的代码中过度使用它们。

`str` 的快捷方式也是一种微优化。Python 中的名称可以是函数的局部名称、模块的全局名称或 Python 的内置名称。查找局部名称比查找全局或内置名称要快。我们已经习惯了 `str` 是一个始终可用的内建函数，但是 Python 仍然需要在每次使用 `str` 时查找它。把它放在本地可以节省我们另一小部分时间，因为局部名称比内建名称查找的更快。

一旦定义了这些快捷方式，我们就可以使用从特定模板创建的 Python 代码了。字符串将使用 `append_result` 或 `extend_result` 的快捷方式添加到 `result` 列表中，具体取决于要添加的字符串是一个还是多个。模板中的文本变成了简单的字符串文本。

同时使用 append 和 extend 会增加复杂性，但请记住，我们的目标是最快地执行模板，对一个项使用 extend 意味着生成一个项的新列表，以便将其传递给 extend。

`{{ ... }}` 中的表达式通过计算被转换为字符串并添加到结果中。表达式中的点由传递到函数中的 `do_dots` 函数处理，因为点表达式的含义取决于上下文中的数据：它可以是属性访问，也可以是子项访问，也可以是可调用的方法。

逻辑结构 `{% if ... %}` 和 `{% for ... %}` 被转换为 Python 条件和循环。`{% if/for ... %}` 标签中的表达式将成为 `if` 或 `for` 语句中的表达式，并且直到 `{% end... %}` 标签之前的内容都将成为语句的主体。

## 编写引擎

现在我们已经了解了引擎将要做什么，接下来让我们介绍一下实现。

### Templite 类

模板引擎的核心是 `Templite` 类。（看明白了吗？它是一个模板（template），但它是精简（lite）的！）

`Templite` 类有一个接口。使用模板的文本构造 `Templite` 对象，然后可以在其上使用 `render` 方法通过模板渲染特定的上下文（即数据字典）：

```py
# 生成Templite对象.
templite = Templite('''
    <h1>Hello {{name|upper}}!</h1>
    {% for topic in topics %}
        <p>You are interested in {{topic}}.</p>
    {% endfor %}
    ''',
    {'upper': str.upper},
)

# 稍后，使用它渲染数据
text = templite.render({
    'name': "Ned",
    'topics': ['Python', 'Geometry', 'Juggling'],
})
```

我们在创建对象时传递模板的文本给它，以便只执行一次编译步骤，然后多次调用 `render` 来重用编译后的结果。

构造函数还接受一个字典作为初始上下文。它们存储在 `Templite` 对象中，并且在以后渲染模板时可用。这些对于定义函数或常量非常有用，我们希望函数或常量在任何地方都可用，就像上一个例子中的 `upper`。

在讨论 `Templite` 的实现之前，我们首先要定义一个辅助函数：`CodeBuilder`。

### CodeBuilder

我们引擎的主要工作是解析模板并生成 Python 代码。为了帮助生成 Python，我们创建了 `CodeBuilder` 类，它在构造 Python 代码时为我们提供辅助功能。它添加代码行，管理缩进，最后从编译的 Python 中给我们提供值。

一个 `CodeBuilder` 对象负责整个 Python 代码块。我们的模板引擎所使用的 Python 块始终是一个完整的函数定义。但是 `CodeBuilder` 类不会假设它是一个函数。这使得 `CodeBuilder` 代码更加通用，与模板引擎代码的其余部分耦合更少。

我们还使用嵌套的 `CodeBuilder`，使我们能够将代码放在函数的开头，即使我们在接近完成之前还不知道它将是什么。

`CodeBuilder` 对象保存一个字符串列表，这些字符串将一起组装成最终的 Python 代码。它唯一需要的其它状态是当前的缩进级别：

```py
class CodeBuilder(object):
    """方便地构建源代码"""

    def __init__(self, indent=0):
        self.code = []
        self.indent_level = indent
```

`CodeBuilder` 做的不多。`add_line` 添加一行新代码，它会自动将文本缩进到当前缩进级别，并提供一个换行符：

```py
    def add_line(self, line):
        """在 code 中添加一行源代码。
        缩进和换行会自动添加，无需提供。
        """
        self.code.extend([" " * self.indent_level, line, "\n"])
```

`indent` 和 `dedent` 增加或减少缩进水平：

```py
    INDENT_STEP = 4      # PEP8 规范

    def indent(self):
        """为后续行增加一个缩进"""
        self.indent_level += self.INDENT_STEP

    def dedent(self):
        """为后续行减少一个缩进"""
        self.indent_level -= self.INDENT_STEP
```

`add_section` 由另一个 `CodeBuilder` 对象管理。这样我们就可以在代码中保留对某个位置的引用，并在以后向其添加文本。`self.code` 列表主要是字符串列表，但也包含对以下部分的引用：

```py
    def add_section(self):
        """添加一个块，一个子 CodeBuilder"""
        section = CodeBuilder(self.indent_level)
        self.code.append(section)
        return section
```

`__str__` 生成一个包含所有代码的字符串。它只是将 `self.code` 中的所有的字符串连接在一起。请注意，因为 `self.code` 可以包含 `section`，这可能会递归调用其它 `CodeBuilder` 对象：

```py
    def __str__(self):
        return "".join(str(c) for c in self.code)
```

`get_globals` 通过执行代码生成最终值。它将对象字符串化，然后执行以获取其定义，并返回结果值：

```py
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
```

最后一种方法使用了 Python 的一些神奇特性。`exec` 函数执行包含 Python 代码的字符串。`exec` 的第二个参数是一个字典，它将收集由代码定义的全局变量。例如，如果我们这样做：

```py
python_source = """\
SEVENTEEN = 17

def three():
    return 3
"""
global_namespace = {}
exec(python_source, global_namespace)
```

那么 `global_namespace['SEVENTEEN']` 是17， `global_namespace['three']` 是一个名为 `three` 的函数。

虽然我们只使用 `CodeBuilder` 来生成一个函数，但是并没有限制只有这个用途。这使得类更易于实现，也更易于理解。

`CodeBuilder` 允许我们创建一个 Python 源代码块，并且对模板引擎没有任何特定的了解。我们可以这样使用它，在 Python 中定义三个不同的函数，然后 `get_globals` 将返回包含这三个函数的 dict。这样我们的模板引擎只需要定义一个函数。但是最好的软件设计是将实现细节保留在模板引擎代码中，而不是在我们的 `CodeBuilder` 类中。

因此我们实际上是用它来定义一个函数，让 `get_globals` 返回字典来使代码更加模块化，因为它不需要知道我们定义的函数的名称。无论我们在 Python 源代码中定义什么函数名，我们都可以从 `get_globals` 返回的 `dict` 中检索该名称。

现在我们可以进入 `Templite` 类本身的实现，看看 `CodeBuilder` 是如何使用以及在哪里使用的。

### Templite 类实现

我们的大部分代码都在 `Templite` 类中。正如我们所讨论的，它既有编译阶段，也有渲染阶段。

#### 编译

将模板编译成 Python 函数的所有工作都发生在 `Templite` 构造函数中。首先，将上下文保存起来：

```py
    def __init__(self, text, *contexts):
        """用给定的“text”构造模板。
        `contexts`是用于将来呈现的值的字典。
        这些对过滤器和全局值很有用。
        """
        self.context = {}
        for context in contexts:
            self.context.update(context)
```

注意我们使用了 `*contexts` 作为参数。星号表示任何数量的参数都将打包到一个元组中并作为 `contexts` 传递。这称为参数解包，意味着调用者可以提供许多不同的上下文字典。下面调用中的任何一个都是有效的：

```py
t = Templite(template_text)
t = Templite(template_text, context1)
t = Templite(template_text, context1, context2)
```

上下文参数（如果有的话）作为 `contexts` 元组提供给构造函数。然后我们可以迭代 `contexts` 元组并依次处理。我们只需创建一个组合字典 `self.context`，它包含上下文的所有内容。如果其中提供了重复的名称，那么后面的会覆盖前面的。

为了使编译后的函数尽可能快，我们将上下文变量提取到 Python 局部变量中。我们将通过保留一组变量名的集合来获得这些名称，我们还需要跟踪模板中定义的变量名，即循环变量：

```py
        self.all_vars = set()
        self.loop_vars = set()
```

稍后我们将看到如何使用这些来帮助构造我们函数的序言(函数序言(function prologue)是函数在启动的时候运行的一系列指令)。首先，我们将使用前面编写的 `CodeBuilder` 类开始构建编译后的函数：

```py
        code = CodeBuilder()

        code.add_line("def render_function(context, do_dots):")
        code.indent()
        vars_code = code.add_section()
        code.add_line("result = []")
        code.add_line("append_result = result.append")
        code.add_line("extend_result = result.extend")
        code.add_line("to_str = str")
```

在这里我们构造 `CodeBuilder` 对象，并向其中加入语句。我们的 Python 函数是 `render_function`，它接受两个参数：`context` 是它应该使用的数据字典，`do_dots` 是一个实现点属性访问的函数。

这里的上下文包含传递给模板构造函数和传递给 `render` 函数的数据上下文，是我们在 `Templite` 构造函数中创建的模板可用的完整数据集。

注意，`CodeBuilder` 非常简单：它不需要知道函数定义，只拥有几行代码。这使得 `CodeBuilder` 的实现和使用都变得简单。我们可以在这里读取生成的代码，而不必费心思插入太多专门的 `CodeBuilder`。

我们创建一个名为 `vars_code` 的片段。并在之后把变量提取部分写入其中。`vars_code` 对象允许我们在函数中保存一个位置，用于之后存放我们获得的信息。

然后编写四条语句，定义一个结果列表，以及该列表的 `append` 和 `extend` 方法的快捷方式，以及 `str()` 内置函数的快捷方式。正如我们前面所讨论的，这只会使渲染功能的性能提高一点。

我们同时拥有 `append` 和 `extend` 方法的快捷方式的原因是，我们可以使用最有效的方法，这取决于我们有一行还是多行要添加到结果中。

接下来，我们定义一个内部函数来帮助我们缓存输出字符串：

```py
        buffered = []
        def flush_output():
            """将 `buffered` 输出到代码生成器"""
            if len(buffered) == 1:
                code.add_line("append_result(%s)" % buffered[0])
            elif len(buffered) > 1:
                code.add_line("extend_result([%s])" % ", ".join(buffered))
            del buffered[:]
```

当我们创建需要进入编译函数的输出块时，我们需要将它们转换为附加到 `result` 的函数调用。我们希望将多次 `append` 调用合并为一个 `extend` 调用。这是另一个微观优化，为了做到这一点，我们缓存了块。

`buffered` 列表保存了尚未写入函数源代码的字符串。随着模板编译的进行，我们将向 `buffered` 追加字符串，并在到达控制流点（如if语句或循环的开始或结束）时将它们刷新到函数源。

`flush_output` 函数是一个闭包，闭包是对引用外部变量的函数的称呼。这里 `flush_output` 引用了 `buffered` 和 `code`。这简化了我们对函数的调用：我们不必告诉 `flush_output` 要刷新哪个缓冲区，或者在哪里刷新它；它隐式地知道所有这些。

如果只缓冲了一个字符串，则使用 `append_result` 的快捷方式将其追加到结果中。如果有多个缓冲区，则会使用 `extend_result` 的快捷方式。然后缓冲列表被清空，以便后续的字符串进入。

其余的编译代码通过将代码行附加到 `buffered` 中向函数添加这些代码行，并最终调用 `flush_output` 将它们写入 `CodeBuilder`。

有了这个函数，我们的编译器中就可以有这样一行代码：

```py
buffered.append("'hello'")
```

这意味着我们编译的 Python 函数将有以下行：

```py
append_result('hello')
```

它将向模板的渲染输出中添加字符串 `hello`。我们这里有多个抽象层次，导致结构不那么清晰。编译器使用 `buffered.append("'hello'")`，它在编译的 Python 函数中创建`append_result('hello')`，当运行时，它将 `hello` 附加到模板结果中。

回到我们的 `Templite` 类。在分析控制结构时，我们需要检查它们是否正确嵌套。`ops_stack` 列表是字符串的堆栈：

```py
        ops_stack = []
```

加入当我们遇到 `{% if .. %}` 标签，我们将把 `'if'` 放进堆栈。当我们找到 `{% endif %}` 标签时，如果堆栈顶部没有 `'if'`，则可以弹出堆栈并报告错误。

现在开始正式解析。我们使用正则表达式（regex）将模板文本拆分为多个部分。正则表达式可能令人望而生畏：它们是用于复杂模式匹配的非常简洁的符号。它们也非常高效，因为匹配模式的复杂部分是在正则表达式引擎中用 C 实现的，而不是在你自己的 Python 代码中实现的。这是我们的正则表达式：

```py
 tokens = re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)
```

这看起来很复杂，让我们把它分解一下。

`re.split` 函数将使用正则表达式拆分字符串。我们的模式是用圆括号括起来的，因此匹配项将用于拆分字符串，拆分后的字符串作为列表中的片段返回。我们的模式将匹配我们的标签语法，但我们将它括起来，以便字符串将在标签处拆分，并且标签也将被返回。

正则表达式中的 `(?s)` 标志意味着一个句点要匹配一个字符，甚至是换行符[^dot]。接下来，在一组园括号中包含三个备选方案：`{{.*?}}` 匹配一个表达式，`{%.*?%}` 匹配一个标签，`{#.*?#}` 匹配一个注释。在它们中，我们使用 `.*?` 匹配任意数量的字符，但匹配的是符合条件的最短序列。

[^dot]: (?s) 即Singleline(单行模式)。表示更改英文句点的含义，使它与每一个字符匹配（包括换行符）。

`re.split` 的结果是字符串列表。例如，下面的模板文本：

```html
<p>Topics for {{name}}: {% for t in topics %}{{t}}, {% endfor %}</p>
```

会被分割成以下片段：

```py
[
    '<p>Topics for ',               # 普通字符串
    '{{name}}',                     # 表达式
    ': ',                           # 普通字符串
    '{% for t in topics %}',        # 标签
    '',                             # 普通字符串（空）
    '{{t}}',                        # 表达式
    ', ',                           # 普通字符串
    '{% endfor %}',                 # 标签
    '</p>'                          # 普通字符串
]
```

一旦文本被拆分成这样的片段，我们就可以循环遍历这些片段，并依次处理。通过按类型拆分它们，我们可以分别处理每种类型。

编译代码是对这些片段进行循环：

```py
        for token in tokens:
```

每个片段都会被检查，以确定是哪种情况。只看前两个字符就足够了。第一种情况是注释，很容易处理：忽略它，然后转到下一个标记：

```py
            if token.startswith('{#'):
                # 注释：忽略并继续
                continue
```

对于 `{{...}}` 表达式，我们将前面和后面的两个大括号切掉，去掉空白，然后将整个表达式传递给 `_expr_code`：

```py
            elif token.startswith('{{'):
                # 要计算的表达式
                expr = self._expr_code(token[2:-2].strip())
                buffered.append("to_str(%s)" % expr)
```

`_expr_code` 方法将模板表达式编译为 Python 表达式。我们稍后再看这个函数。我们使用 `to_str` 函数强制表达式的值为字符串，并将其添加到结果中。

第三种情况处理起来最麻烦：`{% ... %}` 标签。这些将转换成为 Python 控制结构。首先，我们必须刷新缓冲的输出行，然后从标签中提取单词列表：

```py
            elif token.startswith('{%'):
                # 活动标签，拆分成 words 并进一步解析
                flush_output()
                words = token[2:-2].strip().split()
```

现在我们有三种子情况，基于标签中的第一个词：`if`、`for` 或 `end`。`if` 案例展示了我们简单的错误处理和代码生成：

```py
                if words[0] == 'if':
                    # if语句，计算表达式以确定if
                    if len(words) != 2:
                        self._syntax_error("Don't understand if", token)
                    ops_stack.append('if')
                    code.add_line("if %s:" % self._expr_code(words[1]))
                    code.indent()
```

`if` 标签应该有一个表达式，所以 `words` 列表中应该只有两个元素。如果没有，我们使用 `_syntax_error` 辅助方法来抛出一个语法错误异常。我们将 `'if'` 放到 `ops_stack` 上，以便检查 `endif` 标签。`if` 标签的表达式部分被 `_expr_code` 编译成 Python 表达式，并在Python `if` 语句中用作条件表达式。

```py
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
```

我们检查语法并将 `'for'` 放到堆栈上。`_variable` 方法检查变量的语法，并将其添加到我们提供的集合中。这就是我们在编译期间收集所有变量名称的方法。稍后我们将编写函数的序言，在这里我们将取出从上下文中获得的所有变量名。为了正确地完成该操作，我们需要知道我们遇到的所有变量的名称（在 `self.all_vars` 中），以及由循环定义的所有变量的名称（在 `self.loop_vars` 中）。

我们处理的最后一种标签是 `end` 标签；`{% endif %}` 或 `{% endfor %}`。对我们编译的函数源的影响是相同的：只需取消缩进以结束前面的 `if` 或 `for` 语句：

```py
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
```

请注意，结束标签所做的实际工作只有一行：取消函数源代码的缩进。该子句的其余部分都是错误检查，以确保模板的格式正确。这在程序翻译代码中并不罕见。

说到错误处理，如果标签不是 `if`、`for` 或 `end`，那么我们就不知道它是什么，所以抛出一个语法错误：

```py
                else:
                    self._syntax_error("Don't understand tag", words[0])
```

我们已经完成了三种不同的特殊语法（`{{...}}`，`{#...#}`，和 `{%...%}`）。剩下的是文字内容。我们将使用 `repr` 内置函数将文本字符串添加到缓冲输出中，生成一个 Python 字符串文本：

```py
            else:
                # 文字内容，如果不是空的就输出
                if token:
                    buffered.append(repr(token))
```

如果我们不使用 `repr`，那么在我们编译的函数中会出现下面的语句：

```py
append_result(abc)      # Error! abc isn't defined
```

我们需要值被如下方式引用：

```py
append_result('abc')
```

`repr` 函数为我们提供字符串周围的引号，并在需要时提供反斜杠：

```py
append_result('"Don\'t you like my hat?" he asked.')
```

注意，我们首先使用`if token:`检查字符串是否为空，因为没有必要向输出添加空字符串。因为我们的正则表达式在标签语法上进行拆分，相邻标签之间将有一个空片段。这里的检查是一种简单的方法，可以避免将无用的 `append_result("")` 语句放入编译后的函数中。

这就完成了对模板中所有片段的循环。循环完成后，所有模板都已处理完毕。我们要做最后一个检查：如果 `ops_stack` 不为空，那么我们一定缺少一个结束标签。然后将缓冲输出刷新到函数源：

```py
        if ops_stack:
            self._syntax_error("Unmatched action tag", ops_stack[-1])

        flush_output()
```

我们在函数的开头创建了一个 `section`。它的作用是将模板变量从上下文取出并转换为 Python 局部变量。现在我们已经处理了整个模板，我们知道了所有变量的名称，所以我们可以在序言中写下这些代码。

我们需要通过一些工作来知道我们需要定义什么名称。看下我们的模板：

```html
<p>Welcome, {{user_name}}!</p>
<p>Products:</p>
<ul>
{% for product in product_list %}
    <li>{{ product.name }}:
        {{ product.price|format_price }}</li>
{% endfor %}
</ul>
```

这里有两个变量，`user_name` 和 `product`。`all_vars` 集合将同时具有这两个名称，因为这两个名称都用在 `{{...}}` 表达式中。但是只有 `user_name` 需要从序言的上下文中提取，因为 `product` 是由循环定义的。

模板中使用的所有变量都在集合 `all_vars` 中，模板中定义的所有变量都在 `loop_vars` 中。`loop_vars` 中的所有名称都已在代码中定义，因为它们在循环中使用。因此，我们需要将所有 `all_vars` 中不在 `loop_vars` 中的名称获取到：

```py
        for var_name in self.all_vars - self.loop_vars:
            vars_code.add_line("c_%s = context[%r]" % (var_name, var_name))
```

每个名称成为函数序言中的一行，将上下文变量解析成为一个适当命名的局部变量。

我们完成了将模板编译成 Python 函数的大部分工作。我们的函数已经在 `result` 中附加了字符串，所以函数的最后一行只是将它们连接在一起并返回它们：

```py
        code.add_line("return ''.join(result)")
        code.dedent()
```

现在我们已经完成了编译后的 Python 函数源代码的编写，我们需要从 `CodeBuilder` 对象中获取函数本身。`get_globals` 方法执行我们一直在组装的 Python 代码。请记住，我们的代码是一个函数定义（从 `def render_function(..):` 开始），因此执行代码将定义 `render_function`，而不是执行 `render_function` 的主体。

`get_globals` 的结果是代码中定义的值的字典。我们从中获取 `render_function` 值，并将其保存为 `Templite` 对象中的一个属性：

```py
        self._render_function = code.get_globals()['render_function']
```

现在 `self._render_function` 是一个可调用的 Python 函数。我们稍后将在渲染阶段使用它。

#### 编译表达式

我们还没有看到编译过程中的一个重要部分：使用`_expr_code` 方法将模板表达式编译为 Python 表达式。我们的模板表达式可能简单的只有一个名称：

```
{{user_name}}
```

也可能是一个复杂序列包含属性访问和过滤器：

```
{{user.name.localized|upper|escape}}
```

我们的 `_expr_code` 方法将处理所有这些可能性。与任何语言中的表达式一样，我们的表达式都是递归构建的：大表达式由较小的表达式组成。整个表达式使用管道分隔，其中第一个部分再使用点分隔，依此类推。所以我们的函数自然采用递归形式：

```py
    def _expr_code(self, expr):
        """为 `expr` 生成 Python 表达式"""
```

首先要考虑的情况是表达式中包含管道。如果是的话，我们就把它拆分成一个管道段列表。第一个管道段递归地传递给 `_expr_code`，以将其转换为 Python 表达式。

```py
        if "|" in expr:
            pipes = expr.split("|")
            code = self._expr_code(pipes[0])
            for func in pipes[1:]:
                self._variable(func, self.all_vars)
                code = "c_%s(%s)" % (func, code)
```

剩下的每一个管道段都是一个函数的名称。值传递进函数以生成最终值。每个函数名都是一个变量，它被添加到 `all_vars` 中，这样我们就可以在序言中正确地提取它。

如果没有管道，可能会有点。如果是这样的话，就用点拆分。第一部分递归地传递给 `_expr_code`，将其转换为 Python 表达式，然后依次处理每个拆分出来的名称：

```py
        elif "." in expr:
            dots = expr.split(".")
            code = self._expr_code(dots[0])
            args = ", ".join(repr(d) for d in dots[1:])
            code = "do_dots(%s, %s)" % (code, args)
```

下面理解点是如何编译的，要知道模板中的 `x.y` 在 Python 中可能意味着 `x['y']` 或 `x.y`，这取决于哪个可以使用；如果结果是可调用的方法，则调用它。这种不确定性意味着我们必须在运行时而不是编译时确定使用哪种方式。因此，我们将 `x.y.z` 编译成一尝个函数调用 `do_dots(x, 'y', 'z')`。这个函数将试各种访问方法并返回成功的值。

`do_dots` 函数在运行时被传递到编译后的 Python 函数中。稍后我们将看到它的实现。

`_expr_code` 函数中的最后一个子句处理输入表达式中没有管道或点的情况。在这种情况下，表达式只是一个名称。我们将其记录在 `all_vars` 中，并通过其带前缀的 Python 名称访问该变量：

```py
        else:
            self._variable(expr, self.all_vars)
            code = "c_%s" % expr
        return code
```

#### 辅助函数

在编译过程中，我们使用了一些辅助函数。`_syntax_error` 方法只是将错误消息组合在一起并抛出异常：

```py
    def _syntax_error(self, msg, thing):
        """使用 `msg` 引发语法错误，并显示 `thing`"""
        raise TempliteSyntaxError("%s: %r" % (msg, thing))
```

`_variable` 方法帮助我们验证变量名，并将它们添加到编译期间收集的名称集中。我们使用正则检查名称是否是有效的 Python 标识符，然后将它添加到集合中：

```py
    def _variable(self, name, vars_set):
        """跟踪 `name` ，被用作变量
        将 name 添加到 `vars_set`，它是变量名的集合。
        如果 `name` 不合法引发异常
        """
        if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", name):
            self._syntax_error("Not a valid name", name)
        vars_set.add(name)
```

这样，编译代码就完成了！

#### 渲染

剩下的就是渲染代码了。因为我们已经将模板编译成了一个 Python 函数，所以渲染代码没有太多的工作要做。它必须准备好数据上下文，然后调用编译好的 Python 代码：

```py
    def render(self, context=None):
        """通过应用 `context`渲染模板
        `context` 是用来渲染的值的字典
        """
        # 生成完整的context
        render_context = dict(self.context)
        if context:
            render_context.update(context)
        return self._render_function(render_context, self._do_dots)
```

请记住，当我们构造 `Templite` 对象时，我们从一个数据上下文开始。这里我们复制它，然后将它和渲染函数中传入的数据混合。复制是为了使连续的多个渲染调用看不到彼此的数据，而合并是为了让我们只有一个字典用于数据查找。这就是我们如何从提供的多个上下文（模板创建时和渲染时）中构建一个统一的数据上下文。

请注意，传递给 `render` 的数据可能会覆盖传递给 Templite 构造函数的数据。这种情况一般不会发生，因为传递给构造函数的上下文具有全局数据，比如过滤器定义和常量，而传递给 `render` 的上下文是具有该渲染的特定数据。

然后我们只需调用编译的 `render_function`。第一个参数是完整的数据上下文，第二个参数是实现点语义的函数。我们每次都使用相同的实现方式：我们自己的 `_do_dots` 方法。

```py
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
```

在编译过程中，像 `x.y.z` 这样的模板表达式会变成 `do_dots(x, 'y', 'z')`。此函数循环遍历点名称，并将每个点作为属性进行尝试，如果失败，则将其作为键进行尝试。这就是为什么我们的单一模板语法可以灵活地充当 `x.y` 或 `x['y']`。在每个步骤中，我们还检查新值是否可调用，如果是，则调用它。一旦我们处理完成了所有的点名称，生成的值就是我们想要的值。

这里我们再次使用 Python 参数解包（`*dots`），这样`_do_dots` 可以接受任意数量的点名称。这为我们提供了一个灵活的函数，可以处理模板中遇到的任何点表达式。

请注意，在调用 `self._render_function` 时，我们传递了一个用于计算点表达式的函数，但始终传入同一个函数。我们本可以将代码作为编译模板的一部分，但会导致每个模板都有相同的八行代码，这八行代码是模板工作方式定义的一部分，而不是特定模板细节的一部分。像这样实现它比让代码成为编译模板的一部分感觉更清晰。

### 测试

模板引擎提供了一套测试，涵盖了所有的行为和边缘情况。实际上我有点超过了我的 500 行限制：模板引擎是 252 行，测试是 275 行。这是典型的经过良好测试的代码：测试代码多于产品代码。

## 剩下可以改善的地方

全功能模板引擎提供了比我们这里实现的更多的功能。为了减少代码量，我们省略了一些有趣的想法，比如：

- 模板继承和包含
- 自定义标签
- 自动转义
- 参数过滤器
- 像 else 和 elif 这样的复杂逻辑
- 具有多个循环变量的循环
- 空白字符的控制

即便如此，我们的简单模板引擎还是很有用的。实际上，它是在 coverage.py 生成 HTML 报告的模板引擎。

## 总结

用 252 行代码我们得到了一个简单但功能强大的模板引擎。真正的模板引擎有更多的特性，但是这段代码展示了这个过程的基本思想：将模板编译成 Python 函数，然后执行该函数以生成文本结果。























