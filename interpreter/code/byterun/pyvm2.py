"""一个纯 Python 实现的 Python 字节码解释器"""
# 改编自
# 1. pyvm2 作者：Paul Swartz，来自 http://www.twistedmatrix.com/users/z3p/
# 2. byterun 作者：Ned Batchelder，github.com/nedbat/byterun

import dis, operator, sys, collections, inspect, types

class Frame(object):
    def __init__(self, code_obj, global_names, local_names, prev_frame):
        self.code_obj = code_obj
        self.global_names = global_names
        self.local_names = local_names
        self.prev_frame = prev_frame
        self.stack = []

        if prev_frame:
            self.builtin_names = prev_frame.builtin_names
        else:
            self.builtin_names = local_names['__builtins__']
            if hasattr(self.builtin_names, '__dict__'):
                self.builtin_names = self.builtin_names.__dict__

        self.last_instruction = 0
        self.block_stack = []

    # 数据堆栈操作
    def top(self):
        return self.stack[-1]

    def pop(self):
        return self.stack.pop()

    def push(self, *vals):
        self.stack.extend(vals)

    def popn(self, n):
        """从值堆栈中弹出多个值。
        返回一个 `n` 个值的列表，首先返回最深的值
        """
        if n:
            ret = self.stack[-n:]
            self.stack[-n:] = []
            return ret
        else:
            return []

    # 块堆栈操作
    def push_block(self, b_type, handler=None):
        stack_height = len(self.stack)
        self.block_stack.append(Block(b_type, handler, stack_height))

    def pop_block(self):
        return self.block_stack.pop()

    def unwind_block(self, block):
        """当给定的块完成时，展开数据栈上的值"""
        if block.type == 'except-handler':
            # 异常在堆栈上包含 type、 value 和 traceback
            offset = 3
        else:
            offset = 0
        
        while len(self.stack) > block.stack_height + offset:
            self.pop()

        if block.type == 'except-handler':
            traceback, value, exctype = self.popn(3)
            return exctype, value, traceback

Block = collections.namedtuple("Block", "type, handler, stack_height")

class Function(object):
    """
    创建一个真实的函数对象，定义解释器期望的东西。
    """

    # 去掉 '__doc__'
    __slots__ = [
        'func_code', 'func_name', 'func_defaults', 'func_globals',
        'func_locals', 'func_dict', 'func_closure',
        '__name__', '__dict__', 
        '_vm', '_func',
    ]

    def __init__(self, name, code, globs, defaults, closure, vm):
        """你不需要按照这个来理解解释器。"""
        self._vm = vm
        self.func_code = code
        self.func_name = self.__name__ = name or code.co_name
        self.func_defaults = tuple(defaults)
        self.func_globals = globs
        self.func_locals = self._vm.frame.local_names
        self.__dict__ = {}
        self.func_closure = closure
        self.__doc__ = code.co_consts[0] if code.co_consts else None

        # 有时我们需要一个真正的 Python 函数，这里就是
        kw = {
            'argdefs': self.func_defaults,
        }
        if closure:
            kw['closure'] = tuple(make_cell(0) for _ in closure)
        # 利用 types 模块的 FunctionType 生成方法
        self._func = types.FunctionType(code, globs, **kw)

    def __call__(self, *args, **kwargs):
        """调用函数时，创建一个新帧并运行它。"""
        # Python 3.6.1更新（bpo-19611）：
        # 作用域和生成器表达式作用域生成的隐式 .0 参数会变为 implicit0
        # 处理的时候需要注意(在 byte_LOAD_FAST 中)
        callargs = inspect.getcallargs(self._func, *args, **kwargs)
        # 使用 callargs 提供参数的映射：传递到新帧
        frame = self._vm.make_frame(
            self.func_code, callargs, self.func_globals, {}
        )
        return self._vm.run_frame(frame)

def make_cell(value):
    # 创建一个真正的Python闭包并获取一个单元格。
    fn = (lambda x: lambda: x)(value)
    return fn.__closure__[0]


class VirtualMachineError(Exception):
    pass

class VirtualMachine(object):
    def __init__(self):
        self.frames = []  # 帧的调用堆栈
        self.frame = None # 当前帧
        self.return_value = None
        self.last_exception = None

    # 帧处理   
    def make_frame(self, code, callargs={}, global_names=None, local_names=None):
        if global_names is not None and local_names is not None:
            local_names = global_names
        elif self.frames:
            global_names = self.frame.global_names
            local_names = {}
        else:
            global_names = local_names = {
                '__builtins__': __builtins__,
                '__name__': '__main__',
                '__doc__': None,
                '__package__': None
            }
        local_names.update(callargs)
        frame = Frame(code, global_names, local_names, self.frame)
        return frame
    
    def push_frame(self, frame):
        self.frames.append(frame)
        self.frame = frame

    def pop_frame(self):
        self.frames.pop()
        if self.frames:
            self.frame = self.frames[-1]
        else:
            self.frame = None

    # 跳转字节码
    def jump(self, jump):
        """将字节码指针移到 `jump`，以便下一步执行。"""
        self.frame.last_instruction = jump

    def run_code(self, code, global_names=None, local_names=None):
        """使用虚拟机执行代码的入口点。"""
        frame = self.make_frame(code, global_names=global_names, local_names=local_names)

        self.run_frame(frame)
        # Check some invariants
        # if self.frames:
        #     raise VirtualMachineError("Frames left over!")
        # if self.frame and self.frame.stack:
        #     raise VirtualMachineError("Data left on stack! %r" % self.frame.stack)

        # for testing, was val = self.run_frame(frame)
        # return val # for testing

    def parse_byte_and_args(self):
        """解析字节码中的指令和参数
        Python 3.6以上的版本中，每条指令均占2字节，一个字节指令，一个字节参数
        """
        f = self.frame
        opoffset = f.last_instruction
        byteCode = f.code_obj.co_code[opoffset]
        f.last_instruction += 1
        byte_name = dis.opname[byteCode]
        if byteCode >= dis.HAVE_ARGUMENT:
            # 索引到字节码中
            arg = f.code_obj.co_code[f.last_instruction]
            f.last_instruction += 1 # 前进指令指针
            arg_val = int(arg)
            if byteCode in dis.hasconst: # 查找常量
                arg = f.code_obj.co_consts[arg_val]
            elif byteCode in dis.hasname: # 查找名称
                arg = f.code_obj.co_names[arg_val]
            elif byteCode in dis.haslocal: # 查找本地名称
                arg = f.code_obj.co_varnames[arg_val]
            elif byteCode in dis.hasjrel: # 计算相对跳转
                arg = f.last_instruction + arg_val
            else:
                arg = arg_val
            argument = [arg]
        else:
            f.last_instruction += 1 # 即使没有参数也要前进
            argument = []

        return byte_name, argument

    def dispatch(self, byte_name, argument):
        """按 bytename 分派到相应的方法。
        在虚拟机上捕获并设置异常"""
        # 稍后展开块堆栈时，
        # 我们需要知道我们为什么要这么做。
        why = None
        try:
            bytecode_fn = getattr(self, 'byte_%s' % byte_name, None)
            if bytecode_fn is None:
                if byte_name.startswith('UNARY_'):
                    self.unaryOperator(byte_name[6:])
                elif byte_name.startswith('BINARY_'):
                    self.binaryOperator(byte_name[7:])
                else:
                    raise VirtualMachineError(
                        "unsupported bytecode type: %s" % byte_name
                    )
            else:
                why = bytecode_fn(*argument)
        except:
            # 处理执行操作时遇到的异常。
            self.last_exception = sys.exc_info()[:2] + (None,)
            why = 'exception'

        return why
    
    def manage_block_stack(self, why):
        block = self.frame.block_stack[-1]

        if block.type == 'loop' and why == 'continue':
            self.jump(self.return_value)
            why = None
            return why

        self.frame.pop_block()
        current_exc = self.frame.unwind_block(block)
        if current_exc is not None:
            self.last_exception = current_exc

        if block.type == 'loop' and why == 'break':
            self.jump(block.handler)
            why = None

        elif (block.type in ['setup-except', 'finally'] and why == 'exception'):
            self.frame.push_block('except-handler')
            exctype, value, tb = self.last_exception
            self.frame.push(tb, value, exctype)
            self.frame.push(tb, value, exctype) # 2次
            self.jump(block.handler)
            why = None

        elif block.type == 'finally':
            if why in ('return', 'continue'):
                self.frame.push(self.return_value)
            self.frame.push(why)
            self.jump(block.handler)
            why = None

        return why

    def run_frame(self, frame):
        """运行一个帧，直到它（以某种方式）返回。
        异常被抛出，或者返回值被返回
        """
        self.push_frame(frame)
        while True:
            byte_name, argument = self.parse_byte_and_args()
            why = self.dispatch(byte_name, argument)

            # 处理我们需要做的任何块管理
            while why and frame.block_stack:
                why = self.manage_block_stack(why)

            if why:
                break
        
        self.pop_frame()
        if why == 'exception':
            exc, val, tb = self.last_exception
            e = exc(val)
            e.__traceback__ = tb
            raise e

        return self.return_value

    ## 堆栈操作

    def byte_LOAD_CONST(self, const):
        self.frame.push(const)

    def byte_POP_TOP(self):
        self.frame.pop()

    def byte_DUP_TOP(self):
        self.frame.push(self.frame.top())

    ## 名称
    def byte_LOAD_NAME(self, name):
        frame = self.frame
        if name in frame.local_names:
            val = frame.local_names[name]
        elif name in frame.global_names:
            val = frame.global_names[name]
        elif name in frame.builtin_names:
            val = frame.builtin_names[name]
        else:
            raise NameError("name '%s' is not defined" % name)
        self.frame.push(val)

    def byte_STORE_NAME(self, name):
        self.frame.local_names[name] = self.frame.pop()

    def byte_DELETE_NAME(self, name):
        del self.frame.local_names[name]

    def byte_LOAD_FAST(self, name):
        # 特殊处理作用域和生成器表达式作用域生成的隐式.0参数
        if name == '.0':
            name = 'implicit0'
        if name in self.frame.local_names:
            val = self.frame.local_names[name]
        else:
            raise UnboundLocalError(
                "local variable '%s' referenced before assignment" % name
            )
        self.frame.push(val)

    def byte_STORE_FAST(self, name):
        self.frame.local_names[name] = self.frame.pop()

    def byte_LOAD_GLOBAL(self, name):
        f = self.frame
        if name in f.global_names:
            val = f.global_names[name]
        elif name in f.builtin_names:
            val = f.builtin_names[name]
        else:
            # 异常提示信息中不再包含 global
            # raise NameError("global name '%s' is not defined" % name)
            raise NameError("name '%s' is not defined" % name)
        f.push(val)

    ## 操作符

    UNARY_OPERATORS = {
        'POSITIVE': operator.pos,
        'NEGATIVE': operator.neg,
        'NOT':      operator.not_,
        'INVERT':   operator.invert,
    }

    def unaryOperator(self, op):
        x = self.frame.pop()
        self.frame.push(self.UNARY_OPERATORS[op](x))

    BINARY_OPERATORS = {
        'POWER':    pow,
        'MULTIPLY': operator.mul,
        'FLOOR_DIVIDE': operator.floordiv,
        'TRUE_DIVIDE':  operator.truediv,
        'MODULO':   operator.mod,
        'ADD':      operator.add,
        'SUBTRACT': operator.sub,
        'SUBSCR':   operator.getitem,
        'LSHIFT':   operator.lshift,
        'RSHIFT':   operator.rshift,
        'AND':      operator.and_,
        'XOR':      operator.xor,
        'OR':       operator.or_,
    }

    def binaryOperator(self, op):
        x, y = self.frame.popn(2)
        self.frame.push(self.BINARY_OPERATORS[op](x, y))

    COMPARE_OPERATORS = [
        operator.lt,
        operator.le,
        operator.eq,
        operator.ne,
        operator.gt,
        operator.ge,
        lambda x, y: x in y,
        lambda x, y: x not in y,
        lambda x, y: x is y,
        lambda x, y: x is not y,
        lambda x, y: issubclass(x, Exception) and issubclass(x, y),
    ]

    def byte_COMPARE_OP(self, opnum):
        x, y = self.frame.popn(2)
        self.frame.push(self.COMPARE_OPERATORS[opnum](x, y))

    ## 属性和索引

    def byte_LOAD_ATTR(self, attr):
        obj = self.frame.pop()
        val = getattr(obj, attr)
        self.frame.push(val)

    def byte_STORE_ATTR(self, name):
        val, obj = self.frame.popn(2)
        setattr(obj, name, val)

    def byte_STORE_SUBSCR(self):
        val, obj, subscr = self.frame.popn(3)
        obj[subscr] = val

    ## 构建
    def byte_BUILD_TUPLE(self, count):
        elts = self.frame.popn(count)
        e = tuple(elts)
        self.frame.push(e)

    def byte_BUILD_LIST(self, count):
        elts = self.frame.popn(count)
        self.frame.push(elts)

    def byte_BUILD_MAP(self, size):
        self.frame.push({})

    # Python3.6 新增
    def byte_BUILD_CONST_KEY_MAP(self, size):
        """
        The version of BUILD_MAP specialized for constant keys. 
        Pops the top element on the stack which contains a tuple 
        of keys, then starting from TOS1, pops count values to 
        form values in the built dictionary.
        """
        the_map = {}
        keys = self.frame.pop()
        vals = self.frame.popn(size)
        for i in range(size):
            the_map[keys[i]] = vals[i]
        self.frame.push(the_map)

    def byte_STORE_MAP(self):
        the_map, val, key = self.frame.popn(3)
        the_map[key] = val
        self.frame.push(the_map)

    def byte_UNPACK_SEQUENCE(self, count):
        seq = self.frame.pop()
        for x in reversed(seq):
            self.frame.push(x)

    def byte_BUILD_SLICE(self, count):
        if count == 2:
            x, y = self.frame.popn(2)
            self.frame.push(slice(x, y))
        elif count == 3:
            x, y, z = self.frame.popn(3)
            self.frame.push(slice(x, y, z))
        else:           # pragma: no cover
            raise VirtualMachineError("Strange BUILD_SLICE count: %r" % count)

    def byte_LIST_APPEND(self, count):
        val = self.frame.pop()
        the_list = self.frame.stack[-count] # peek
        the_list.append(val)

    ## 跳转

    def byte_JUMP_FORWARD(self, jump):
        self.jump(jump)

    def byte_JUMP_ABSOLUTE(self, jump):
        self.jump(jump)

    def byte_POP_JUMP_IF_TRUE(self, jump):
        val = self.frame.pop()
        if val:
            self.jump(jump)

    def byte_POP_JUMP_IF_FALSE(self, jump):
        val = self.frame.pop()
        if not val:
            self.jump(jump)

    def byte_JUMP_IF_TRUE_OR_POP(self, jump):
        val = self.frame.top()
        if val:
            self.jump(jump)
        else:
            self.frame.pop()

    def byte_JUMP_IF_FALSE_OR_POP(self, jump):
        val = self.frame.top()
        if not val:
            self.jump(jump)
        else:
            self.frame.pop()

    ## 块

    def byte_SETUP_LOOP(self, dest):
        self.frame.push_block('loop', dest)

    def byte_GET_ITER(self):
        self.frame.push(iter(self.frame.pop()))

    def byte_FOR_ITER(self, jump):
        iterobj = self.frame.top()
        try:
            v = next(iterobj)
            self.frame.push(v)
        except StopIteration:
            self.frame.pop()
            self.jump(jump)

    def byte_BREAK_LOOP(self):
        return 'break'

    def byte_CONTINUE_LOOP(self, dest):
        # 这是一个返回值的技巧，展开块时，continue 和 return 都必须
        # 在执行 finally 块时保持状态。
        # 对于 continnue，它是跳转到哪里，对于 return，它是返回的值。
        # 它被压入堆栈，多以 continue 将跳转目的放入 return_value。
        self.return_value = dest
        return 'continue'

    def byte_SETUP_EXCEPT(self, dest):
        self.frame.push_block('setup-except', dest)

    def byte_SETUP_FINALLY(self, dest):
        self.frame.push_block('finally', dest)

    def byte_BEGIN_FINALLY(self, const):
        self.byte_LOAD_CONST(const)

    def byte_END_FINALLY(self):
        v = self.pop()
        if isinstance(v, str):
            why = v
            if why in ('return', 'continue'):
                self.return_value = self.pop()
            if why == 'silenced':       # PY3
                block = self.pop_block()
                assert block.type == 'except-handler'
                self.unwind_block(block)
                why = None
        elif v is None:
            why = None
        elif issubclass(v, BaseException):
            exctype = v
            val = self.pop()
            tb = self.pop()
            self.last_exception = (exctype, val, tb)
            why = 'reraise'
        else:       # pragma: no cover
            raise VirtualMachineError("Confused END_FINALLY")
        return why

    def byte_POP_BLOCK(self):
        self.frame.pop_block()

    def byte_RAISE_VARARGS(self, argc):
        cause = exc = None
        if argc == 2:
            cause = self.frame.pop()
            exc = self.frame.pop()
        elif argc == 1:
            exc = self.frame.pop()
        return self.do_raise(exc, cause)
    
    def do_raise(self, exc, cause):
        if exc is None: # 重新引发
            exc_type, val, tb = self.last_exception
        elif type(exc) == type:  # 像 `raise ValueError`
            exc_type = exc
            val = exc()  # 生成一个实例
        elif isinstance(exc, BaseException):
            # 像 `raise ValueError('foo')`
            exc_type = type(exc)
            val = exc
        else:
            return 'exception' # 失败

        self.last_exception = exc_type, val, val.__traceback__
        return 'exception'

    def byte_POP_EXCEPT(self):
        block = self.frame.pop_block()
        if block.type != 'except-handler':
            raise Exception("popped block is not an except handler")
        current_exc = self.frame.unwind_block(block)
        if current_exc is not None:
            self.last_exception = current_exc

    ## 函数和方法
    def byte_LOAD_METHOD(self, arg):
        self.byte_LOAD_ATTR(arg)

    def byte_CALL_METHOD(self, arg):
        self.byte_CALL_FUNCTION(arg)

    def byte_MAKE_FUNCTION(self, argc):
        # 这个方法在3.6变了
        # argc代表 flags
        # 0x01 a tuple of default values for positional-only and positional-or-keyword parameters in positional order
        # 0x02 a dictionary of keyword-only parameters’ default values
        # 0x04 an annotation dictionary
        # 0x08 a tuple containing cells for free variables, making a closure
        name = self.frame.pop()
        code = self.frame.pop()
        # 这个地方还需要优化
        defaults =  self.frame.pop() if (argc & 1) == 1 else []
        globs = self.frame.global_names
        #TODO: if we're not supporting kwargs, do we need the defaults?
        fn = Function(name, code, globs, defaults, None, self)
        self.frame.push(fn)

    def byte_CALL_FUNCTION(self, arg):
        lenKw, lenPos = divmod(arg, 256) # 前8位 KWargs not supported in byterun
        # 仅对只有positional arguments有效
        posargs = self.frame.popn(lenPos)

        func = self.frame.pop()
        retval = func(*posargs)       
        self.frame.push(retval)

    def byte_RETURN_VALUE(self):
        self.return_value = self.frame.pop()
        return "return"

    ## 导入

    def byte_IMPORT_NAME(self, name):
        level, fromlist = self.frame.popn(2)
        frame = self.frame
        self.frame.push(__import__(name, frame.global_names, 
            frame.local_names, fromlist, level))

    def byte_IMPORT_FROM(self, name):
        mod = self.frame.top()
        self.frame.push(getattr(mod, name))

    ## 其它...
    def byte_STORE_LOCALS(self):
        self.frame.local_names = self.frame.pop()

    def byte_LOAD_BUILD_CLASS(self):
        self.frame.push(self.build_class)

    def build_class(self, func, name, *bases, **kwds):
        if not isinstance(func, Function):
            raise TypeError("func must be a Function")
        if not isinstance(name, str):
            raise TypeError("name must be string")
        metaclass = kwds.pop('metaclass', None)
        if metaclass is None:
            metaclass = type(bases[0]) if bases else type
        if isinstance(metaclass, type):
            metaclass = self.calculate_metaclass(metaclass, bases)

        void = object()
        prepare = getattr(metaclass, '__prepare__', void)
        namespace = {} if prepare is void else prepare(name, bases, **kwds)

        frame = Frame(func.func_code, func.func_globals, namespace, self.frame)
        self.run_frame(frame)

        cls = metaclass(name, bases, namespace)
        return cls

    def calculate_metaclass(self, metaclass, bases):
        winner = metaclass
        for base in bases:
            t = type(base)
            if issubclass(t, winner):
                winner = t
            elif not issubclass(winner, t):
                raise TypeError("metaclass conflict", winner, t)
        return winner

    



    







            

    