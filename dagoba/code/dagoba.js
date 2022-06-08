/*
     ____  _____ _____ _____ _____ _____ 
    |    \|  _  |   __|     | __  |  _  |
    |  |  |     |  |  |  |  | __ -|     |
    |____/|__|__|_____|_____|_____|__|__|
    
    dagoba: a tiny in-memory graph database
    ex: 
    V = [ {name: 'alice'}                                         // alice gets auto-_id (prolly 1)
        , {_id: 10, name: 'bob', hobbies: ['asdf', {x:3}]}] 
    E = [ {_out: 1, _in: 10, _label: 'knows'} ]
    g = Dagoba.graph(V, E)
    
    g.addVertex({name: 'charlie', _id: 'charlie'})                // string ids are fine
    g.addVertex({name: 'delta', _id: '30'})                       // in fact they're all strings
    g.addEdge({_out: 10, _in: 30, _label: 'parent'})
    g.addEdge({_out: 10, _in: 'charlie', _label: 'knows'})
    g.v(1).out('knows').out().run()                               // returns [charlie, delta]
    
    q = g.v(1).out('knows').out().take(1)
    q.run()                                                       // returns [charlie]
    q.run()                                                       // returns [delta]    (but don't rely on result order!)
    q.run()                                                       // returns []
    Dagoba consists of two main parts: graphs and queries.
    A graph contains vertices and edges, and provides access to query initializers like g.v()
    A query contains pipes, which make up a pipeline, and a virtual machine for processing pipelines.
    There are some pipe types defined by default.
    There are also a few helper functions.
    That's all.
    copyright dann toliver, 2015
    version 0.3.3
*/

// 命名空间
Dagoba = {} 

// 原型
Dagoba.G = {} 

// 工厂
Dagoba.graph = function(V, E) { 
    var graph = Object.create(Dagoba.G);
    graph.edges = [];  
    graph.vertices = [];
    graph.vertexIndex = {};
    graph.autoid = 1; // 自增id计数器
    if(Array.isArray(V)) { // 仅接受数组
        graph.addVertices(V);
    }
    if(Array.isArray(E)) {
        graph.addEdges(E);
    }
    return graph;
}

// 查询初始化器
Dagoba.G.v = function() { 
    var query = Dagoba.query(this);
    query.add('vertex', [].slice.call(arguments)); // 添加顶点作为第一个查询管道
    return query;
}

// 添加顶点
Dagoba.G.addVertex = function(vertex) {
    if(!vertex._id) {
        vertex._id = this.autoid++;
    } else if(this.findVertexById(vertex._id)) {
        return Dagoba.error('A vertext with id ' + vertex._id + ' already exists')
    }

    this.vertices.push(vertex);
    this.vertexIndex[vertex._id] = vertex;
    vertex._out = [];
    vertex._in = [];
    return vertex._id;
}

// 添加边
Dagoba.G.addEdge = function(edge) {
    edge._in = this.findVertexById(edge._in);
    edge._out = this.findVertexById(edge._out);

    // 边要包含入和出的顶点
    if(!(edge._in && edge._out)) {
        return Dagoba.error("That edge's " + (edge._in ? 'out' : 'in') + "vertex wasn't found")
    }
    edge._out._out.push(edge);
    edge._in._in.push(edge);
    this.edges.push(edge);
}

// 添加顶点数组
Dagoba.G.addVertices = function(vertices) {
    vertices.forEach(this.addVertex.bind(this));
}
// 添加边数组
Dagoba.G.addEdges = function(edges) {
    edges.forEach(this.addEdge.bind(this));
}

// 通用顶点发现函数
Dagoba.G.findVertices = function(args) { 
    if(typeof args[0] == 'object') {
        return this.searchVertices(args[0]);
    } else if(args.length == 0) {
        return this.vertices.slice();
    } else {
        return this.findVerticesByIds(args);
    }
}

// 根据ID数组查找顶点
Dagoba.G.findVerticesByIds = function(ids) {
    if(ids.length == 1) {
        var maybe_vertex = this.findVertexById(ids[0]);
        return maybe_vertex ? [maybe_vertex] : []
    }
    return ids.map(this.findVertexById.bind(this)).filter(Boolean);
}

// 根据ID查找顶点
Dagoba.G.findVertexById = function(vertex_id) {
    return this.vertexIndex[vertex_id];
}

// 根据过滤条件查找顶点
Dagoba.G.searchVertices = function(filter) {
    return this.vertex.filter(function(vertex) {
        return Dagoba.objectFilter(vertex, filter);
    });
}

// 查找顶点的出边
Dagoba.G.findOutEdges = function(vertex) {
    return vertex._out;
}

// 查找顶点的入边
Dagoba.G.findInEdges = function(vertex) {
    return vertex._in;
}

// 序列化
Dagoba.G.toString = function() {
    return Dagoba.jsonify(this);
}

// 反序列化
Dagoba.fromString = function(str) {
    var obj = JSON.parse(str);
    return Dagoba.graph(obj.V, obj.E);
}


// 原型
Dagoba.Q = {}

// 工厂，仅被图的查询初始化器调用
Dagoba.query = function(graph) {
    var query = Object.create(Dagoba.Q);

    query.graph = graph; // 图
    query.state = []; // 每步的状态
    query.program = []; // 步骤列表
    query.gremlins = []; // 每步的gremlin

    return query;
}

Dagoba.Q.run = function() {
    this.program = Dagoba.transform(this.program);

    var max = this.program.length - 1; // program 中的最后一步
    var maybe_gremlin = false; // 一个 gremlin，一个信号字符串或者一个 false
    var results = []; // 运行结果
    var done = -1; // 已经结束的事情
    var pc = max; // program 计数器，从结尾开始

    var step, state, pipetype;

    while(done < max) {
        step = this.program[pc];
        state = (this.state[pc] = this.state[pc] || {});
        pipetype = Dagoba.getPipetype(step[0])

        maybe_gremlin = pipetype(this.graph, step[1], maybe_gremlin, state)

        if(maybe_gremlin == 'pull') {
            maybe_gremlin = false;
            if(pc - 1 > done) {
                pc--;
                continue;
            } else {
                done = pc;
            }
        }

        if(maybe_gremlin == 'done') {
            maybe_gremlin = false;
            done = pc;
        }

        pc++;

        if(pc > max) {
            if(maybe_gremlin) {
                results.push(maybe_gremlin);
            }
            maybe_gremlin = false;
            pc--;
        }
    }

    results = results.map(function(gremlin) {
        return gremlin.result != null ? gremlin.result : gremlin.vertex;
    });

    return results;
}

// 添加一个新步骤step到查询中
Dagoba.Q.add = function(pipetype, args) {
    // step是一个数组，由管道类型和参数组成
    var step = [pipetype, args]
    this.program.push(step);
    return this;
}

// 管道类型对象
Dagoba.Pipetypes = {}

// 向查询中添加新方法
Dagoba.addPipetype = function(name, fun) {
    Dagoba.Pipetypes[name] = fun;
    Dagoba.Q[name] = function() {
        return this.add(name, [].slice.apply(arguments));
    }
}

// 获取pipetype，其实是一个函数
Dagoba.getPipetype = function(name) {
    var pipetype = Dagoba.Pipetypes[name];
    if(!pipetype) {
        Dagoba.error('Unrecognized pipe type: ' + name);
    }
    return pipetype || Dagoba.fauxPipeType;
}

// 找不到管道类型时的默认方法
Dagoba.fauxPipetype = function(graph, args, maybe_gremlin) {
    return maybe_gremlin || 'pull'
}

Dagoba.addPipetype('vertex', function(graph, args, gremlin, state) {
    if(!state.vertices) {
        // 状态初始化
        state.vertices = graph.findVertices(args);
    }
    // 所有工作完成
    if(!state.vertices.length) {
        return 'done';
    }
    var vertex = state.vertices.pop();
    // 返回 gremlin
    return Dagoba.makeGremlin(vertex, gremlin.state)
});

Dagoba.simpleTraversal = function(dir) {
    var find_method = dir == 'out' ? 'findOutEdges' : 'findEdges';
    var edge_list = dir == 'out' ? '_in' : '_out';

    return function(graph, args, gremlin, state) {
        if(!gremlin && (!state.edges || !state.edges.length)) {
            return 'pull';
        }

        if(!state.edges || !state.edges.length) {
            state.gremlin = gremlin;
            state.edges = graph[find_method](gremlin.vertex)
                .filter(Dagoba.filterEdges(args[0]));
        }

        if(!state.edges.length) {
            return 'pull';
        }

        var vertex = state.edges.pop()[edge_list];
        return Dagoba.gotoVertex(state.gremlin, vertex);
    }
}

Dagoba.addPipetype('in', Dagoba.simpleTraversal('in'));
Dagoba.addPipetype('out', Dagoba.simpleTraversal('out'));

Dagoba.addPipetype('property', function(graph, args, gremlin, state) {
    if(!gremlin) {
        return 'pull';
    }
    gremlin.result = gremlin.vertex[args[0]];
    return gremlin.result == null ? false : gremlin;
});

Dagoba.addPipetype('unique', function(graph, args, gremlin, state) {
    if(!gremlin) {
        return 'pull';
    }
    if(state[gremlin.vertex._id]) {
        return 'pull';
    }
    state[gremlin.vertex._id] = true;
    return gremlin;
});

Dagoba.addPipetype('filter', function(graph, args, gremlin, state) {
    if(!gremlin) {
        return 'pull';
    }
    if(typeof args[0] == 'object') {
        return Dagoba.objectFilter(gremlin.vertex, args[0])? gremlin : 'pull';
    }
    if(typeof args[0] != 'function') {
        Dagoba.error('Filter arg is not a function: ' + args[0]);
        return gremlin;
    }

    if(!args[0](gremlin.vertex, gremlin)) {
        return 'pull';
    }
    return gremlin;
});

Dagoba.addPipetype('take', function(graph, args, gremlin, state) {
    state.taken = state.taken || 0;

    if(state.taken == args[0]) {
        state.taken = 0;
        return 'done';
    }
    if(!gremlin) {
        return 'pull';
    }
    state.taken++;
    return gremlin;
});

Dagoba.addPipetype('as', function(graph, args, gremlin, state) {
    if(!gremlin) {
        return 'pull';
    }
    gremlin.state.as = gremlin.state.as || {};
    gremlin.state.as[args[0]] = gremlin.vertex;
    return gremlin;
});

Dagoba.addPipetype('back', function(graph, args, gremlin, state) {
    if(!gremlin) {
        return 'pull';
    }
    return Dagoba.gotoVertex(gremlin, gremlin.state.as[args[0]]);
});

Dagoba.addPipetype('except', function(graph, args, gremlin, state) {
    if(!gremlin) {
        return 'pull';
    }
    if(gremlin.vertex == gremlin.state.as[args[0]]) {
        return 'pull';
    }
    return gremlin;
});

Dagoba.addPipetype('merge', function(graph, args, gremlin, state) {
    if(!state.vertices && !gremlin) {
        return 'pull';
    }
    if(!state.vertices || !state.vertices.length) {
        var obj = (gremlin.state || {}).as || {};
        state.vertices = args.map(function(id) {
            return obj[id];
        }).filter(Boolean);
    }
    if(!state.vertices.length) {
        return 'pull';
    }
    var vertex = state.vertices.pop();
    return Dagoba.makeGremlin(vertex, gremlin.state);
});

// 辅助函数

Dagoba.makeGremlin = function(vertex, state) {
    return {vertex: vertex, state: state || {}}
}

Dagoba.gotoVertex = function(gremlin, vertex) {
    return Dagoba.makeGremlin(vertex, gremlin.state);
}

Dagoba.filterEdges = function(filter) {
    return function(edge) {
        if(!filter) {
            return true;
        }

        if(typeof filter == 'string') {
            return edge._label == filter;
        }

        if(Array.isArray(filter)) {
            return !!~filter.indexOf(edge._label);
        }

        return Dagoba.objectFilter(edge, filter);
    }
}

// 过滤器
Dagoba.objectFilter = function(thing, filter) {
    for(var key in filter) {
        if(thing[key] !== filter[key]) {
            return false;
        }
    }
    return true;
}

Dagoba.cleanVertex = function(key, value) {
    return (key == '_in' || key == '_out') ? undefined : value;
}

Dagoba.cleanEdge = function(key, value) {
    return (key == '_in' || key == '_out') ? value._id : value;
}

Dagoba.jsonify = function(graph) {
    return '{"V":' + JSON.stringify(graph.vertices, Dagoba.cleanVertex)
        + ',"E":' + JSON.stringify(graph.edges, Dagoba.cleanEdge)
        + '}';
}

Dagoba.persist = function(graph, name) {
    name = name || 'graph';
    localStorage.setItem('DAGOBA::' + name, graph);
}

Dagoba.depersist = function(name) {
    name = 'DAGOBA::' + (name || 'graph');
    var flatgraph = localStorage.getItem(name);
    return Dagoba.fromString(flatgraph);
}

Dagoba.error = function(msg) {
    console.log(msg);
    return false;
}

Dagoba.T = [];

// 转换器
Dagoba.addTransformer = function(fun, priority) {
    if(typeof fun != 'function') {
        return Dagoba.error('Invalid tranformer function');
    }
    for(var i = 0; i < Dagoba.T.length; i++) {
        if(priority > Dagoba.T[i].priority) {
            break;
        }
    }
    Dagoba.T.splice(i, 0, {priority: priority, fun: fun});
}

Dagoba.transform = function(program) {
    return Dagoba.T.reduce(function(acc, transformer) {
        return transformer.fun(acc);
    }, program);
}

Dagoba.addAlias = function(newname, oldname, defaults) {
    defaults = defaults || [];
    Dagoba.addPipetype(newname, function() {});
    Dagoba.addTransformer(function(program) {
        return program.map(function(step) {
            if(step[0] != newname) {
                return step;
            }
            return [oldname, Dagoba.extend(step[1], defaults)]
        });
    }, 100);
}

Dagoba.extend = function(list, defaults) {
    return Object.keys(defaults).reduce(function(acc, key) {
        if(typeof list[key] != 'undefined') {
            return acc;
        }
        acc[key] = defaults[key];
        return acc;
    }, list);
}

