0.7
---
- Add memory_level, processor_level to work script
- Remove redundant calls to data_type.load
- Render run_tool_json errors in form
- Replace setup script with support for setup.sh in work script
- Replace show_standard_output, show_standard_error with show_raw_output
- Support inline default values in tool configuration e.g. {--x} and {--x 1}
- Use hard links when available

0.6
---
- Accept markdown templates that lack titles
- Add work script
- Expand support for DataType.parse, DataType.render
- Handle empty arguments properly
- Rearrange result folder
- Recognize variable name and variable help in markdown templates

0.5
---
- Serve Python Jupyter Notebooks
- Support Python 3
- Support Unicode
- Support Windows

0.4
---
- Add tool scaffold
- Support data types that require extra stylesheets, scripts, api_keys
- Make result files available from server
- Use DataTypeError to detect data_type errors
- Use DataType classmethods without instantiation

0.3
---
- Validate standard outputs and standard errors against data types
- Support popovers via help in tool definition

0.2
---
- Support data type plugins
- Add setup script

0.1
---
- Add run script
- Add serve script
