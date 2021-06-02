# author: LeadroyaL

from com.pnfsoftware.jeb.client.api import IScript, IGraphicalClientContext
from com.pnfsoftware.jeb.core.units.code.java import IJavaSourceUnit

FMT = """{js_wrap_name}
    .{method_name}
    .overload({param_list})
    .implementation = function (...args) {{ // for javascript
        console.log("before hooked {method_sig}");
        let ret = this.{method_name}({args_list});
        console.log("after hooked {method_sig}");
        return ret;
    }};"""


FMT_RET_VOID = """{js_wrap_name}
    .{method_name}
    .overload({param_list})
    .implementation = function (...args) {{ // for javascript
        console.log("before hooked {method_sig}");
        this.{method_name}({args_list});
        console.log("after hooked {method_sig}");
    }};"""

class FastClassFrida(IScript):
    def run(self, ctx):
        if not isinstance(ctx, IGraphicalClientContext):
            print ('This script must be run within a graphical client')
            return
        if not isinstance(ctx.getFocusedView().getActiveFragment().getUnit(), IJavaSourceUnit):
            print ('This script must be run within IJavaSourceUnit')
            return
        java_source_unit = ctx.getFocusedView().getActiveFragment().getUnit()   #IJavaSourceUnit
        java_class = java_source_unit.getClassElement()     # IJavaClass
        class_name = self.to_frida(java_class.getName())
        js_wrap_name = "jswp_" + class_name.replace(".", "_")
        print('==== start ====')
        print("""var {} = Java.use("{}");""".format(js_wrap_name, self.to_frida(java_class.getName())))
        for method in java_class.getMethods():
            method_name = method.getName()
            method_sig = method.getSignature()
            method_params = []
            for param in method.getParameters():
                method_params.append('"' + self.to_frida( param.getType().getSignature()) + '"')

            ret_void = method.getReturnType().isVoid()

            if ret_void:
                print FMT_RET_VOID.format(
                    js_wrap_name=js_wrap_name, 
                    method_name=method_name, 
                    param_list=','.join(method_params[1:]),
                    method_sig=method_sig,
                    args_list=self.gen_args(method_params[1:])
                )
            else:
                print FMT.format(
                    js_wrap_name=js_wrap_name, 
                    method_name=method_name, 
                    param_list=','.join(method_params[1:]),
                    method_sig=method_sig,
                    args_list=self.gen_args(method_params[1:])
                )

    def gen_args(self, params):
        return ','.join(['args[%d]' % i for i in range(len(params))])

    def to_frida(self, param):
        # input: [I, return: [I
        # input: [Ljava/lang/String; return: [Ljava.lang.String;
        if param[0] == '[':
            return param.replace('/', '.')
        # input: Ljava/lang/String; return: java.lang.String
        # input: I, return: int
        else:
            if param[-1] == ';':
                return param[1:-1].replace('/', '.')
            else:
                return self.basicTypeMap[param[0]]

    basicTypeMap = {'C': u'char',
                    'B': u'byte',
                    'D': u'double',
                    'F': u'float',
                    'I': u'int',
                    'J': u'long',
                    'L': u'ClassName',
                    'S': u'short',
                    'Z': u'boolean',
                    '[': u'Reference',
                    }

    def split(self, params):
        ret = []
        offset = 0
        length = len(params)
        while offset < length:
            startIdx = offset
            while params[offset] == '[':
                offset += 1
            char = params[offset]
            if char == 'L':
                end = params.index(';', offset)
                ret.append(params[startIdx: end + 1])
                offset = end
            elif char in self.basicTypeMap:
                ret.append(params[startIdx: offset + 1])
            offset += 1
        return ret