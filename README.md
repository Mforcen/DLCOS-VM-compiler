# Culebra VM compiler
This is a compiler to generate bytecode for the VM inside the project [DL_COS](https://github.com/Mforcen/DL_COS).

This language is inspired by Python, sharing lots of grammar, but it is static.
Uses lark to parse the source code, and an example can be found inside the test.fl file.

There are some builtin functions inside the Compiler_VMBuiltin.h file that is found in the repository, although
they are implemented in the DL_COS project.