from atexit import register
from utils.symbol_table import *
import utils.AST as AST
from utils.node_visitor import NodeVisitor
import config


class IRGenerator(NodeVisitor):

    reginster_index = 0
    label_index = 0

    def __init__(self):
        self.create_and_push_builtin_funcs()
    
    
    def visit_Prog1(self, node, table):
        #print(f"visiting: prog1")
        func_code = self.visit(node.func, config.global_symbol_table)
        code = func_code

        #add used builtint functions
        self.builtin_funcs.reverse()
        for i in range(len(self.builtin_funcs)):
            if self.builtin_funcs[i]["used"] and not self.builtin_funcs[i]["included"] :
                code = f'''{self.builtin_funcs[i]["code"]}
{code}'''
                self.builtin_funcs[i]["included"] = True
        config.IR_code = self.delete_empty_lines_from_code(code)
        self.free_memory()
        return code

    def visit_Prog2(self, node, table):
        #print(f"visiting: prog2")
        func_code = self.visit(node.func,config.global_symbol_table)
        prog_code = self.visit(node.prog, config.global_symbol_table)
        func_name = node.func.iden.iden_value["name"]

        #the following if-else statmement makes sure that "main" function always come after all other functions
        if func_name == "main":
            code = prog_code  + "\n" + func_code
        else:
            code = func_code + "\n" + prog_code

        #add used builtint functions
        self.builtin_funcs.reverse()
        for i in range(len(self.builtin_funcs)):
            if self.builtin_funcs[i]["used"] and not self.builtin_funcs[i]["included"] :
                code = f'''{self.builtin_funcs[i]["code"]}
{code}'''
                self.builtin_funcs[i]["included"] = True

        config.IR_code = self.delete_empty_lines_from_code(code)
        self.free_memory()
        return code


    def visit_Func(self, node, table):
        #print(f"visiting: func")
        function_iden= node.iden.iden_value["name"]
        function_symbol = table.get(function_iden)
        function_iden = function_symbol.name
        function_body_block = self.find_symbol_table(f"{function_iden}_function_body_block_table", table)

        parameters = self.get_parameters(node)

        self.reginster_index = 0
        parameters_initiation_code = ""
        for param in parameters:
            self.initiate_var_symbol_register(param["iden"].iden_value["name"], function_body_block)


        func_body_code = self.visit(node.body, function_body_block)
        code = f'''proc {function_iden}
{parameters_initiation_code}
{func_body_code}'''
        return code
        
        

    def visit_Body1(self, node, table):
        #print(f"visiting: body1")
        stmt_code = self.visit(node.stmt, table)
        code = stmt_code
        if not stmt_code:
            code = ""
        else:
            code = stmt_code
        return code


    def visit_Body2(self, node, table):
        #print(f"visiting: body2")
        stmt_code = self.visit(node.stmt, table)
        body_code = self.visit(node.body, table)

        if not stmt_code:
            code = body_code
        else:
            code = f'''{stmt_code}{body_code}'''
        return code 


    def visit_Stmt1(self, node, table):
        #print(f"visiting: stmt1")
        res = self.visit(node.expr, table)
        if res:
            expr_code = res["code"]
            code = expr_code
        else: 
            code =""
        return code
            

    def visit_Stmt2(self, node, table):
        #print(f"visiting: stmt2")
        res = self.visit(node.defvar, table)

        code = res
        return code
        


    def visit_Stmt3(self, node, table):
        #print(f"visiting: stmt3")
        res = self.visit(node.expr, table)
        expr_code = res["code"]
        expr_returned_reg = res["reg"]
        if_block_symbol_table = self.find_symbol_table(f"if_block_{node.lineno}", table) # symbol table for "if" block
        stmt_code = self.visit(node.stmt, if_block_symbol_table)

        label = self.create_label()
        code = f'''{expr_code}
\tjz {expr_returned_reg}, {label}
{stmt_code}
{label}:'''

        return code

        

        


    def visit_Stmt4(self, node, table):
        #print(f"visiting: stmt4")
        res = self.visit(node.expr, table)
        expr_code = res["code"]
        expr_returned_reg = res["reg"]

        if_block_symbol_table = self.find_symbol_table(f"if_block_{node.lineno}", table) # symbol table for "if" block
        stmt_code = self.visit(node.stmt, if_block_symbol_table)

        else_block_symbol_table = self.find_symbol_table(f"else_block_{node.lineno}", table) # symbol table for "else" block
        stmt2_code = self.visit(node.stmt2, else_block_symbol_table)

        label = self.create_label()
        code = f'''{expr_code}
\tjz {expr_returned_reg}, {label}
{stmt_code}
{label}:
{stmt2_code}'''

        return code



    def visit_Stmt5(self, node, table):
        #print(f"visiting: stmt5")
        res = self.visit(node.expr, table)
        expr_code = res["code"]
        expr_returned_reg = res["reg"]

        do_block_symbol_table = self.find_symbol_table(f"do_block_{node.lineno}", table) # symbol table for "do" block of a while
        stmt_code = self.visit(node.stmt, do_block_symbol_table)

        label = self.create_label()
        code = f'''{expr_code}
\tjz {expr_returned_reg}, {label}
{stmt_code}
{label}:'''

        return code


    def visit_Stmt6(self, node, table):
        #print(f"visiting: stmt6")
        foreach_block_symbol_table = self.find_symbol_table(f"foreach_block_{node.lineno}", table) # symbol table for "foreach" block

        name = node.iden.iden_value["name"]
        iden_reg = self.initiate_var_symbol_register(name, foreach_block_symbol_table)

        res = self.visit(node.expr, table)
        expr_code = res["code"]
        expr_returned_reg = res["reg"]

        res2 = self.visit(node.stmt, foreach_block_symbol_table)
        stmt_code = res2

        expr_type = getattr(node, "type")
        

        if expr_type == "Int":
            tmp_reg = self.create_register()
            tmp_reg2 = self.create_register()
            label = self.create_label()
            label2 = self.create_label()
            code = f'''{expr_code}
\tmov {iden_reg}, 0   
{label}:
\tcmp< {tmp_reg}, {iden_reg}, {expr_returned_reg}
\tjz {tmp_reg}, {label2}
{stmt_code}
\tmov {tmp_reg2}, 1
\tadd {iden_reg}, {tmp_reg2}, {iden_reg}
\tjmp {label}
{label2}:'''


        elif expr_type == "Array":
            tmp_reg = self.create_register()
            tmp_reg2 = self.create_register()
            tmp_reg3 = self.create_register()
            tmp_reg4 = self.create_register()
            tmp_reg5 = self.create_register()
            tmp_reg6 = self.create_register()
            tmp_reg7 = self.create_register()
            label = self.create_label()
            label2 = self.create_label()
            code = f'''
\tld {tmp_reg}, {expr_returned_reg}
\tmov {tmp_reg2}, 0
\tmov {tmp_reg3}, {expr_returned_reg}
\tmov {tmp_reg4}, {8}
\tadd {tmp_reg3}, {tmp_reg3}, {tmp_reg4}
{label}:
\tcmp< {tmp_reg5}, {tmp_reg2}, {tmp_reg}
\tjz {tmp_reg5}, {label2}
\tld {tmp_reg6}, {tmp_reg3}
\tmov {iden_reg}, {tmp_reg6}
{stmt_code}
\tmov {tmp_reg7}, 1
\tadd {tmp_reg2}, {tmp_reg2}, {tmp_reg7}
\tadd {tmp_reg3}, {tmp_reg3}, {tmp_reg4}
\tjmp {label}
{label2}:'''
        return code        



    def visit_Stmt7(self, node, table):
        #print(f"visiting: stmt7")
        res = self.visit(node.expr, table)
        expr_code = res["code"]
        expr_returned_reg = res["reg"]

        code = f'''{expr_code}
    mov r0, {expr_returned_reg}
    ret'''
        return code
            


    def visit_Stmt8(self, node, table):
        #print(f"visiting: stmt8")
        body_block_symbol_table = self.find_symbol_table(f"body_block_{node.lineno}", table) # symbol table for "body" block
        body_code = self.visit(node.body, body_block_symbol_table)
        code = body_code
        return code

    
    def visit_Defvar(self, node, table):
        #print(f"visiting: defvar")
        name = node.iden.iden_value["name"]
        type = node.type.type_value["name"]
        reg = self.initiate_var_symbol_register(name, table)

        code = f'''
    mov {reg}, {0}'''
        return code
        

            
    def visit_Expr1(self, node, table):
        #print(f"visiting: expr1")
        #function call
        function_iden = node.iden.iden_value["name"]
        for i in range(len(self.builtin_funcs)):
            if function_iden == self.builtin_funcs[i]["name"] :
                self.builtin_funcs[i]["used"] = True

        arguments = self.get_arguments(node, table)

        arguments_registers_string = ""
        arguments_codes_string = ""

        returning_reg = self.create_register()



        for i in range(len(arguments)):
            if i == 0:
                if len(arguments) == 1:
                    arguments_registers_string += f"{returning_reg}"
                else:
                     arguments_registers_string += f"{returning_reg}, "
                arguments_codes_string += f'''{arguments[i]['code']}
    mov {returning_reg}, {arguments[0]["reg"]}'''


            elif i == len(arguments) - 1: 
                arguments_registers_string += f"{arguments[i]['reg']}"
                arguments_codes_string += f"{arguments[i]['code']}"

            else:
                arguments_registers_string += f"{arguments[i]['reg']}, "
                arguments_codes_string += f"{arguments[i]['code']}, "


        if not arguments:
            return {"reg": returning_reg, 
            "code" : f'''call {function_iden}, {returning_reg}'''}


        else:            
            return {"reg": returning_reg, 
            "code" : f'''{arguments_codes_string}
    call {function_iden}, {arguments_registers_string}'''}



    def visit_Expr2(self, node, table):
        #print(f"visiting: expr2")
        # calling an Array
        res = self.visit(node.expr, table)
        array_iden_reg = res["reg"]

        res2 = self.visit(node.expr2, table)
        expr2_returned_code = res2["code"]
        expr2_returned_reg = res2["reg"]

        tmp_reg = self.create_register()
        tmp_reg2 = self.create_register()
        tmp_reg3 = self.create_register()
        tmp_reg4 = self.create_register()


        #by calling an array with format "A[n]", reg which contains the value of that specific array cell, and also 
        #addr which contains address of that cell, is being return
        return {"reg": tmp_reg4, "addr":tmp_reg3,
        "code" : f'''{expr2_returned_code}
\tmov {tmp_reg}, 1
\tmov {tmp_reg2}, 8
\tadd {tmp_reg}, {expr2_returned_reg}, {tmp_reg}
\tmul {tmp_reg2}, {tmp_reg}, {tmp_reg2}
\tadd {tmp_reg3}, {array_iden_reg}, {tmp_reg2}
\tld {tmp_reg4}, {tmp_reg3}'''}




    def visit_Expr3(self, node, table):
        #print(f"visiting: expr3")
        res = self.visit(node.expr, table)
        expr_returned_code = res["code"]
        expr_returned_reg = res["reg"]

        res2 = self.visit(node.expr2, table)
        expr2_returned_code = res2["code"]
        expr2_returned_reg = res2["reg"]

        res3 = self.visit(node.expr3, table)
        expr3_returned_code = res3["code"]
        expr3_returned_reg = res3["reg"]

        
        tmp_reg = self.create_register()
        label = self.create_label()
        label2 = self.create_label()
        return {"reg": tmp_reg, 
        "code" : f'''{expr_returned_code}
\tjz {expr_returned_reg}, {label}
{expr2_returned_code}
\tmov {tmp_reg}, {expr2_returned_reg}
\jmp {label2}
{label}:
{expr3_returned_code}
\tmov {tmp_reg}, {expr3_returned_reg}
{label2}:'''}




    def visit_Expr4(self, node, table):
        #print(f"visiting: expr4")
        operator = node.oper["name"]

        res = self.visit(node.expr, table)
        expr_returned_code = res["code"]
        expr_returned_reg = res["reg"]

        res2 = self.visit(node.expr2, table)
        expr2_returned_code = res2["code"]
        expr2_returned_reg = res2["reg"]

        if operator == "=":
            #check if the left-hand side expr is an Array
            if isinstance(node.expr, AST.Expr2):
                address_of_that_cell_of_array = res["addr"]
                tmp_reg = self.create_register()
                return {"reg": tmp_reg, 
                "code" : f'''
{expr_returned_code}
{expr2_returned_code}
\tst {expr2_returned_reg}, {address_of_that_cell_of_array}'''}   

            else:
                return {"reg": expr_returned_reg, 
                "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tmov {expr_returned_reg}, {expr2_returned_reg}'''}
        
        if operator == "+":
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tadd {expr_returned_reg}, {expr_returned_reg}, {expr2_returned_reg}'''}
        
        if operator == "-":
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tsub {expr_returned_reg}, {expr_returned_reg}, {expr2_returned_reg}'''}

        if operator == "*":
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tmul {expr_returned_reg}, {expr_returned_reg}, {expr2_returned_reg}'''}
        
        if operator == "/":
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tdiv {expr_returned_reg}, {expr_returned_reg}, {expr2_returned_reg}'''}

        if operator == "%":
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tmod {expr_returned_reg}, {expr_returned_reg}, {expr2_returned_reg}'''}
        
        if operator == "<":
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tcmp< {expr_returned_reg}, {expr_returned_reg}, {expr2_returned_reg}'''}

        if operator == ">":
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tcmp> {expr_returned_reg}, {expr_returned_reg}, {expr2_returned_reg}'''}

        if operator == "==":
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tcmp= {expr_returned_reg}, {expr_returned_reg}, {expr2_returned_reg}'''}
        
        if operator == "<=":
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tcmp<= {expr_returned_reg}, {expr_returned_reg}, {expr2_returned_reg}'''}

        if operator == ">=":
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tcmp>= {expr_returned_reg}, {expr_returned_reg}, {expr2_returned_reg}'''}

        if operator == "!=":
            label = self.create_label()
            label2 = self.create_label()

            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tcmp= {expr_returned_reg}, {expr_returned_reg}, {expr2_returned_reg}
\tjz {expr_returned_reg}, {label}
\tmov {expr_returned_reg}, 0
\tjmp {label2}
{label}:
\tmov {expr_returned_reg}, 1
{label2}:'''}

        if operator == "||":
            label = self.create_label()
            label2 = self.create_label()
            label3 = self.create_label()
            
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tjz {expr_returned_reg}, {label}
\tmov {expr_returned_reg}, 1
\tjmp {label3}
{label}: 
\tjz {expr2_returned_reg}, {label2}
\tmov {expr_returned_reg}, 1
\tjmp {label3}
{label2}: 
\tmov {expr_returned_reg}, 0
{label3}:'''}

        if operator == "&&":
            label = self.create_label()
            label2 = self.create_label()
            label3 = self.create_label()
            
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
{expr2_returned_code}
\tjz {expr_returned_reg}, {label2}
\tjz {expr2_returned_reg}, {label2}
{label}:
\tmov {expr_returned_reg}, 1
\tjmp {label3}
{label2}:
\tmov {expr_returned_reg}, 0
{label3}:'''}


    def visit_Expr5(self, node, table):
        #print(f"visiting: expr5")
        operator = node.oper["name"]

        res = self.visit(node.expr, table)
        expr_returned_code = res["code"]
        expr_returned_reg = res["reg"]


        if operator == "!":
            label = self.create_label()
            label2 = self.create_label()
            return {"reg": expr_returned_reg, 
            "code" : f'''{expr_returned_code}
\tjz {expr_returned_reg}, {label}
\tmov {expr_returned_reg}, 0
\tjmp {label2}
{label}:
\tmov {expr_returned_reg}, 1
{label2}:'''}

        if operator == "+":
            return {"reg": expr_returned_reg,
            "code" : expr_returned_code}
        
        if operator == "-":
            tmp_reg = self.create_register()
            return {"reg": expr_returned_reg,
            "code" : f'''{expr_returned_code}
\tmov {tmp_reg}, 2
\tmul {tmp_reg}, {expr_returned_reg}, {tmp_reg}
\tsub {expr_returned_reg}, {tmp_reg}, {expr_returned_reg}'''}



    def visit_Expr6(self, node, table):
        #print(f"visiting: expr6")
        res = self.visit(node.expr, table)
        expr_returned_code = res["code"]
        expr_returned_reg = res["reg"]
        return {"reg": expr_returned_reg,
        "code" : expr_returned_code}


    def visit_Expr7(self, node, table):
        #print(f"visiting: expr7")
        name = node.iden.iden_value["name"]
        iden_reg = table.get(name).reg
        return {"reg": iden_reg,
        "code" : ""}
        

    def visit_Expr8(self, node, table):
        #print(f"visiting: expr8")pr
        num = self.visit(node.num, table)
        num_reg = self.create_register()
        return {"reg": num_reg ,
        "code" : f'''
\tmov {num_reg}, {num}'''}
        


    # flist rules are handled inside visit_func


    def visit_Clist1(self, node, table):
        #print(f"visiting: clist1")
        pass


    def visit_Clist2(self, node, table):
        #print(f"visiting: clist2")
        return self.visit(node.expr, table)
        

    def visit_Clist3(self, node, table):
        #print(f"visiting: clist3")
        self.visit(node.clist, table)
        return self.visit(node.expr, table)

    def visit_Num(self, node, table):
        #print(f"visiting: num")
        num = node.num_value["name"]
        return num




    builtin_funcs = []
    def create_and_push_builtin_funcs(self):

        self.builtin_funcs.append({"name":"getInt", "used":False, "included":False,
        "code":'''proc getInt
    call iget, r0
    ret'''})


        self.builtin_funcs.append({"name":"printInt", "used":False, "included":False,
        "code":'''proc printInt
    call iput, r0
    ret'''})



        #It allocate cells of memory with size of 8*n (n is length of the array, the argument to this function)
        #and it reterns a register with the address if the first cell of the Array
        #also first cell of the Array has the value of n (length of the Array)
        self.builtin_funcs.append({"name":"createArray", "used":False, "included":False,
        "code":'''proc createArray
    mov r1, 1
    add r1, r0, r1
    mov r2, 8
    mul r2, r1, r2
    call mem, r2
    st r0, r2
    mov r0, r2
    ret'''})


        
        #Argument of this function is the Array's identifer ( getArray(A) ), in lower level it is an register with the address of the first cell of the array
        #and it contains the length of the Array
        self.builtin_funcs.append({"name":"getArray", "used":False, "included":False,
        "code":'''proc getArray
    ld r1, r0
    mov r2, 1   
    mov r3, 8   
label_getArray:
    cmp<= r4, r2, r1
    jz r4, label2_getArray
    mul r4, r2, r3
    add r5, r0, r4
    call iget, r6
    st r6, r5
    mov r7, 1
    add r2, r2, r7
    jmp label_getArray
label2_getArray:
    ret'''})


        #Argument of this function is the Array's identifer ( getArray(A) ), in lower level it is an register with the address of the first cell of the array
        #and it contains the length of the Array
        self.builtin_funcs.append({"name":"printArray", "used":False, "included":False,
        "code":'''proc printArray
    ld r1, r0
    mov r2, 1   
    mov r3, 8   
label_printArray:
    cmp<= r4, r2, r1
    jz r4, label2_printArray
    mul r4, r2, r3
    add r5, r0, r4
    ld r6, r5
    call iput, r6
    mov r7, 1
    add r2, r2, r7
    jmp label_printArray
label2_printArray:
    ret'''})


        self.builtin_funcs.append({"name":"arrayLength", "used":False, "included":False,
        "code":'''proc arrayLength
    ld r1, r0
    mov r0, r1
    ret'''})

    def create_register(self):
        self.reginster_index += 1
        return f"r{self.reginster_index - 1}"

    
    def create_label(self, name=None):
        self.label_index += 1
        if name:
            return f"{name}{self.label_index - 1}"
        return f"label{self.label_index - 1}"


    def find_symbol_table(self, name, parent):
        for i in range(len(parent.children)):
            if parent.children[i].name == name:
                return parent.children[i]


    def get_parameters(self, node):
        parameters = []
        flist = node.flist
        if not isinstance(flist, AST.Empty):
            if flist.iden:
                parameters.append({"iden": flist.iden, "type": flist.type})
            while hasattr(flist, "flist"):
                flist = flist.flist
                if (not isinstance(flist, AST.Empty)):
                    parameters.append({"iden": flist.iden, "type": flist.type})
        #parameters.reverse()
        return parameters


    def get_arguments(self, node, table):
        #get arguments
        arguments = []
        clist = node.clist
        if not isinstance(clist, AST.Empty):
            if clist.expr:
                res = self.visit(clist, table)
                expr_returned_code = res["code"]
                expr_returned_reg = res["reg"]
                if not isinstance(res, str) and res:
                    res = expr_returned_reg
                arguments.append({"reg": expr_returned_reg, "code": expr_returned_code})
                while hasattr(clist, "clist"):
                    clist = clist.clist
                    if (not isinstance(clist, AST.Empty)):
                        res = self.visit(clist, table)
                        expr_returned_code = res["code"]
                        expr_returned_reg = res["reg"]
                        if not isinstance(res, str):
                            res = expr_returned_reg
                        arguments.append({"reg": expr_returned_reg, "code": expr_returned_code})
        return arguments

    def initiate_var_symbol_register(self, name, table):
        var_symbol = table.get(name)
        reg = self.create_register()
        setattr(var_symbol, "reg", reg)
        return reg

    
    def update_var_symbol_register(self, name, value, table):
        var_symbol = table.get(name)
        code = f"\tmov {var_symbol}, {value}"
        return code

    def delete_empty_lines_from_code(self, code):
        lines = code.split("\n")
        non_empty_lines = [line for line in lines if line.strip() != ""]
        modified_code = ""
        for line in non_empty_lines:
            modified_code += line + "\n"

        #because only after keyword "ret", there should be an empty line
        modified_code = modified_code.replace("ret", "ret\n")
        return modified_code



    def free_memory(self):
        pass
