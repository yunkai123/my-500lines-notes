"""与图类型相关的输出例程"""

def as_graphviz(graph):
    """渲染 contingent.Graph 成为 graphviz 代码

    要将此例程的输出保存为图像，你可以将文本保存在名为 output.dot 的文件
    中，然后运行：

    $ dot -Tpng output.dot > output.png
    """

    edges = graph.edges()
    inputs = set(input for input, consequence in edges)
    consequences = set(consequence for input, consequence in edges)
    lines = ['digraph {', 'graph [rankdir=LR];']
    append = lines.append

    def node(task):
        return '"{}"'.format(task)

    append('node [fontname=Arial shape=rect penwidth=2 color="#DAB21D"')
    append('      style=filled fillcolor="#F4E5AD"]')

    append('{rank=same')
    for task in graph.sorted(inputs - consequences):
        append(node(task))
    append('}')

    append('node [shape=rect penwidth=2 color="#708BA6"')
    append('      style=filled fillcolor="#DCE9ED"]')

    append('{rank=same')
    for task in graph.sorted(consequences - inputs):
        append(node(task))
    append('}')

    append('node [shape=oval penwidth=0 style=filled fillcolor="#E8EED2"')
    append('      margin="0.05, 0"]')

    for task, consequence in edges:
        append('{} -> {}'.format(node(task), node(consequences)))

    append('}')
    return '\n'.join(lines)