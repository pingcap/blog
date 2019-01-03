---
title: Adding Built-in Functions
date: 2016-12-19
summary: TiDB code is updated and the procedure of adding built-in functions is greatly simplified. This document describes how to add built-in functions to TiDB.
tags: ['TiDB', 'Engineering', 'Golang']
aliases: ['/blog/2016/12/19/adding-built-in-function/']
categories: ['Engineering']
---

This document describes how to add built-in functions to TiDB.

- [Background](#background)
- [The procedure to add a built-in function](#the-procedure-to-add-a-built-in-function)
- [Example](#example)

### Background

How is the SQL statement executed in TiDB?

The SQL statement is parsed to an abstract syntax tree (AST) by the parser first and then uses Query Optimizer to generate an execution plan. The plan can then be executed to get the result. This process involves how to access the data in the table, and how to filter, calculate, sort, aggregate, and distinct the data, etc. For a built-in function, the most important part is to parse and to evaluate. 

For parsing, it is redundant work because you should know how to write YACC commands and how to modify TiDB syntax parser. But we have finished this work for you and syntax parsing of most built-in functions is done. 

As for evaluation, it should be finished in the TiDB expression evaluation framework. Each built-in function is considered as an expression indicated by `ScalarFunction` and obtains the corresponding function type and function signature through the function name and parameters to evaluate. 

The procedure discussed above is complicated for users who are not familiar with TiDB. We have finished syntax parsing and function signature confirmation of most unimplemented functions. But implementation is left empty. In other words, locating and completing the  empty implementation makes a Pull Request (PR).

### The procedure to add a built-in function

The following procedure describes how to add a built-in function.

1. Locate the unimplemented function.

    1. Search for `errFunctionNotExists` in the `expression` directory of TiDB source code. You can find all the unimplemented functions.

    2. Choose a function you are interested in. Take the SHA2 function as an example:

        ```
        func (b *builtinSHA2Sig) eval(row []types.Datum) (d types.Datum, err error) {
        return d, errFunctionNotExists.GenByArgs("SHA2")
        }
        ```

2. Implement the function signature. 

    This step is to implement `eval`. For the function features, see MySQL documentation. For the specific implementation method, see the method of implemented functions. 

3. Add the type inference information to the `typeinferer` file.

    Add the type of the returned result of the function to `handleFuncCallExpr()` in the the `plan/typeinferer.go` file and make sure the result is consistent with the result in MySQL. See [MySQL Const](https://github.com/pingcap/tidb/blob/rc2.3/mysql/type.go#L17) for the complete list of the type definition.

    **Note:** For most fuctions, you need to input the type of the returned result and obtain the length of the returned result.

4. Add a unit test case.

    Add a unit test case for the function to the `expression` directory. Add a unit test case of `typeinferer` to the `plan/typeinferer_test.go` file. 

5. Run the `make dev` command and make sure all the test cases can pass.

### Example

Take the [Pull Request](https://github.com/pingcap/tidb/pull/2781/files) to add the `SHA1()` function as an example:

1. Open the `expression/builtin_encryption.go` file and complete the evaluation of `SHA1()`.

    ```
    func (b *builtinSHA1Sig) eval(row []types.Datum) (d types.Datum, err error) {
        // Evaluate the arguments. In most cases, you do not need to make any modification.
        args, err := b.evalArgs(row)
        if err != nil {
            return types.Datum{}, errors.Trace(err)
        }
        // See MySQL documentation for the meaning of each argument.
        // SHA/SHA1 function only accept 1 parameter
        arg := args[0]
        if arg.IsNull() {
            return d, nil
        }
        // The type of the argument value is changed. See "util/types/datum.go" for the function implementation.    
        bin, err := arg.ToBytes()
        if err != nil {
            return d, errors.Trace(err)
        }
        hasher := sha1.New()
        hasher.Write(bin)
        data := fmt.Sprintf("%x", hasher.Sum(nil))
        // Set the return value.
        d.SetString(data)
        return d, nil
    }
    ```
    
2. Add a unit test case for the function implementation. See `expression/builtin_encryption_test.go`:

    ```
    var shaCases = []struct {
        origin interface{}
        crypt  string
     }{
        {"test", "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"},
        {"c4pt0r", "034923dcabf099fc4c8917c0ab91ffcd4c2578a6"},
        {"pingcap", "73bf9ef43a44f42e2ea2894d62f0917af149a006"},
        {"foobar", "8843d7f92416211de9ebb963ff4ce28125932878"},
        {1024, "128351137a9c47206c4507dcf2e6fbeeca3a9079"},
        {123.45, "22f8b438ad7e89300b51d88684f3f0b9fa1d7a32"},
     }

     func (s *testEvaluatorSuite) TestShaEncrypt(c *C) {
        defer testleak.AfterTest(c)() // The tool for monitoring goroutine leak. You can just copy it.
        fc := funcs[ast.SHA]
        for _, test := range shaCases {
            in := types.NewDatum(test.origin)
            f, _ := fc.getFunction(datumsToConstants([]types.Datum{in}), s.ctx)
            crypt, err := f.eval(nil)
            c.Assert(err, IsNil)
            res, err := crypt.ToString()
            c.Assert(err, IsNil)
            c.Assert(res, Equals, test.crypt)
        }
        // test NULL input for sha
        var argNull types.Datum
        f, _ := fc.getFunction(datumsToConstants([]types.Datum{argNull}), s.ctx)
        crypt, err := f.eval(nil)
        c.Assert(err, IsNil)
        c.Assert(crypt.IsNull(), IsTrue)
    }
    ```
    
    > **Note:** Besides conventional cases, you had better add some exceptional cases in which, for example, the input value is "nil" or the arguments of various types.
      
3. Add the type inference information and the test case. See `plan/typeinferer.go` and `plan/typeinferer_test.go`:

    ```
    case ast.SHA, ast.SHA1:
        tp = types.NewFieldType(mysql.TypeVarString)
        chs = v.defaultCharset
        tp.Flen = 40
    ``` 
    
    ```
        {`sha1(123)`, mysql.TypeVarString, "utf8"},
        {`sha(123)`, mysql.TypeVarString, "utf8"},
    ```
