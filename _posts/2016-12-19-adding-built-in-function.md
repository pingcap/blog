---
layout: post
title: Adding Built-in Functions
excerpt: This document describes how to add built-in functions to TiDB.
---

This document describes how to add built-in functions to TiDB. 

+ [Background](#background)
+ [The procedure to add a built-in function](#the-procedure-to-add-a-built-in-function)
+ [Example](#example)

### Background

How is the SQL statement executed in TiDB?

The SQL statement is parsed to an abstract syntax tree (AST) by the parser first and then uses the optimizer to generate an execution plan. The plan can then be executed to get the result. This process involves how to access the data in the table, and how to filter, calculate, sort, aggregate, and distinct the data, etc. For a built-in function, the most important part is to parse and to evaluate. See the following two sections for further details:

#### Parse
The code for syntax parsing is in the [parser](https://github.com/pingcap/tidb/tree/master/parser) directory and mainly involves the two files: [`misc.go`](https://github.com/pingcap/tidb/blob/master/parser/misc.go) and [`parser.y`](https://github.com/pingcap/tidb/blob/master/parser/parser.y). In the TiDB project, run the `make parser` command to use `goyacc` to convert the `parser.y` file to the `parser.go` file. The code in the `parser.go` file can be called by other `go` code for parsing.

The process to parse the SQL statement to be structured is as follows:

1. Use Scanner to segment the text to tokens. Each token has a name and value. The name is used to match the pre-defined rules in `parser.y` in the parser. 
2. When the rules are being matched, tokens are obtained continuously from the Scanner. If a rule is completely matched, the token that is matched will be replaced by a new variable. Meanwhile, after each rule is matched, the value in the token can be used to construct the node of subtree in AST. 
3. The general format of a built-in function is: `name(args)`. Scanner needs to recognize all the elements of the function, including the name, the parenthesis, and the arguments. The pre-defined rule to be matched in the parser constructs a node in AST. The node contains the arguments and the method for evaluation of the function for the following evaluation.

#### Evaluation

To evaluate is to get the value of the function or the expression based on the input arguments and the runtime environment. The controlling logic is in the [`evaluator/evaluator.go`](https://github.com/pingcap/tidb/blob/master/evaluator/evaluator.go) file. Most of the built-in functions are parsed to `FuncCallExpr`. The process to evaluate is as follows:

1. Convert `ast.FuncCallExpr` to `expression.ScalarFunction`.
2. Call the `NewFunction()` method in the [`expression/scalar_function.go`](https://github.com/pingcap/tidb/blob/master/expression/scalar_function.go).
3. Use `FnName` to find the corresponding function in the `builtin.Funcs` table which is in the [`evaluator/builtin.go`](https://github.com/pingcap/tidb/blob/master/evaluator/builtin.go) file.
4. Call the evaluation function when evaluating `ScalarFunction`.

### The procedure to add a built-in function

/1. Edit the [`misc.go`](https://github.com/pingcap/tidb/blob/master/parser/misc.go) and [`parser.y`](https://github.com/pingcap/tidb/blob/master/parser/parser.y) files.

1).  Add a rule to the `tokenMap` in the [`misc.go`](https://github.com/pingcap/tidb/blob/master/parser/misc.go) file and parse the function name to a token.

2).  Add a rule to [`parser.y`](https://github.com/pingcap/tidb/blob/master/parser/parser.y) and transfer the token sequence to an AST node.

3).  Add a unit test case for parser in the [`parser_test.go`](https://github.com/pingcap/tidb/blob/master/parser/parser_test.go) file.
  
/2. Add the evaluation function to the [`executor`](https://github.com/pingcap/tidb/tree/master/executor) directory.

1). Implement the function in the `evaluator/builtin_xx.go` file. 
	
**Note:** The functions in the [`executor`](https://github.com/pingcap/tidb/tree/master/executor) directory are categorized to several files. For example, `builtin_time.go` is a time-related function. The interface of the function is:
		
```
type BuiltinFunc func([]types.Datum, context.Context) (types.Datum, error)
```
	
2). Register the name and the implementation to [`builtin.Funcs`](https://github.com/pingcap/tidb/blob/master/evaluator/builtin.go#L43).
  
/3. Add the Type Inference information to the [plan/typeinferer.go](https://github.com/pingcap/tidb/blob/master/plan/typeinferer.go) file. Add the type of the returned result of the function to `handleFuncCallExpr()` in the the [plan/typeinferer.go](https://github.com/pingcap/tidb/blob/master/plan/typeinferer.go) file and make sure the result is consistent with the result in MySQL. See [MySQL Const](https://github.com/pingcap/tidb/blob/master/mysql/type.go#L17) for the complete list of the type definition.
/4. Add a unit test case for the function to the [evaluator](https://github.com/pingcap/tidb/tree/master/evaluator) directory.
/5. Run the `make dev` command and make sure all the test cases can pass.

### Example

Take the [Pull Request](https://github.com/pingcap/tidb/pull/2249) to add the `timediff()` function as an example:

/1. Add an entry to the `tokenMap` in the [`misc.go`](https://github.com/pingcap/tidb/blob/master/parser/misc.go) file: 
	
```	
var tokenMap = map[string]int{
"TIMEDIFF":            timediff,
}
```
	
Here, a rule is defined: If the text is found to be `timediff`, it is converted to a token with the name `timediff`. 

**Note:** SQL is case-insensitive, so the capital letters must be used in the `tokenMap`. 

The text in `tokenMap` must be taken as a special token instead of an identifier. In the following parser rule, the token needs special processing as is shown in [`parser/parser.y`](https://github.com/pingcap/tidb/blob/master/parser/parser.y):
	
```
%token	<ident>
timediff	"TIMEDIFF"	
```
	
Which means after the "timediff" token is obtained from the lexer, it is named "TIMEDIFF” and this name will be used for the following rule matching.

The "timediff" here must correspond to the "timediff" of the value in `tokenMap`. When the `parser.y` file is generated to the `parser.go` file, "timediff" will get a token ID which is an INT.
	
Because "timediff" is not a keyword in MySQL, the rule is added to `FunctionCallNonKeyword` in the [`parser.y`](https://github.com/pingcap/tidb/blob/master/parser/parser.y) file:
	
```	
|	"TIMEDIFF" '(' Expression ',' Expression ')'
	{
		$$ = &ast.FuncCallExpr{
			FnName: model.NewCIStr($1),
			Args: []ast.ExprNode{$3.(ast.ExprNode), $5.(ast.ExprNode)},
		}
	}		
```
	
Here it means: If the token sequence matches the pattern, the tokens are specified as a new variable with the name: `FunctionCallNonKeyword` (The value of `FunctionCallNonKeyword` can be assigned by assigning values to the `$$` variable.), which is a node in AST and the type is `*ast.FuncCallExpr`. The value of the `FnName` member variable is the content of `$1`, which is the value of the first token in the rule.
	
"timediff()” is successfully converted to an AST node. Its member variable, `FnName`, has recorded the function name, ”timediff”, for the following evaluation.

**Note:** To use the value of a certain token in the rule, you can use the `$x` format in which `x` is the location of the token in the rule. In the above example, `$1` is `"TIMEDIFF"`，$2 is `’(’`, and $3 is `’)’`. The meaning of `$1.(string)` is to reference the value of the first token and to declare it to be a `string`.

/2. Register the function in the `Funcs` table in the [`builtin.go`](https://github.com/pingcap/tidb/blob/master/evaluator/builtin.go) file:

```
ast.TimeDiff:         {builtinTimeDiff, 2, 2},	
```
	
The arguments are explained as follows:

+ `builtinTimediff`: The implementation of the `timediff` function is included in the `builtinTimediff` function.
+ `2`: The minimum number of the arguments of the function is `2`.
+ `2`: The maximum number of the arguments of the function is `2`. 

**Note:** The number of the arguments will be checked to see if it's legal during the syntax parsing.

The implementation of the function is in the the [`builtin.go`](https://github.com/pingcap/tidb/blob/master/evaluator/builtin.go) file. See the following for further details:
	
```	
func builtinTimeDiff(args []types.Datum, ctx context.Context) (d types.Datum, err error) {
	sc := ctx.GetSessionVars().StmtCtx
	t1, err := convertToGoTime(sc, args[0])
	if err != nil {
		return d, errors.Trace(err)
	}
	t2, err := convertToGoTime(sc, args[1])
	if err != nil {
		return d, errors.Trace(err)
	}
	var t types.Duration
	t.Duration = t1.Sub(t2)
	t.Fsp = types.MaxFsp
	d.SetMysqlDuration(t)
	return d, nil
}	
```
	
/3. Add the Type Inference information:

```	
case "curtime", "current_time", "timediff":
    tp = types.NewFieldType(mysql.TypeDuration)
    tp.Decimal = v.getFsp(x)	    
```

/4. Add the unit test case:

```	
func (s *testEvaluatorSuite) TestTimeDiff(c *C) {
	// Test cases from https://dev.mysql.com/doc/refman/5.7/en/date-and-time-functions.html#function_timediff
	tests := []struct {
		t1        string
		t2        string
		expectStr string
	}{
		{"2000:01:01 00:00:00", "2000:01:01 00:00:00.000001", "-00:00:00.000001"},
		{"2008-12-31 23:59:59.000001", "2008-12-30 01:01:01.000002", "46:58:57.999999"},
	}
	for _, test := range tests {
		t1 := types.NewStringDatum(test.t1)
		t2 := types.NewStringDatum(test.t2)
		result, err := builtinTimeDiff([]types.Datum{t1, t2}, s.ctx)
		c.Assert(err, IsNil)
		c.Assert(result.GetMysqlDuration().String(), Equals, test.expectStr)
	}
}	
```
