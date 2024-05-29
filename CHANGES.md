# 0.9
- Start from scratch
- Restore self-contained server
- Add views: link, string, number, password, email, text, markdown, image
- Add views: radio, checkbox, table, frame, json, pdf, file
- Move map views into crosscompute-views-map
- Parallelize built-in workers
- Respect GET parameters for views based on string or text
- Refresh variables without reloading page
- Run batches with process or thread concurrency
- Save identities to debug/identities.dictionary
- Save ports to debug/ports.dictionary
- Support script.function
- Support authorization configuration
- Support display.pages > configuration.design
- Support environment > interval to re-run automation batches periodically
- Support environment > engine=podman to run automation in a container
- Support log variables
- Support `_print` parameter for printing
- Support `_embed` parameter for embedding
- Migrate from pyramid to fastapi
- Replace polling with server side events for mutation tracking
- Send variable value and configuration in server side events when possible
- Support live print preview
- Support conditional templates
- Support copyright attribution
- Add basic support for offline form submissions thanks to @zoek1
- Save client ip address in debug/identities.dictionary
- Return JSONResponse if variable value is a dictionary or list (see crosscompute-views-chart)
- Prefer yaml vs yml suffix
- Support `VariableView.has_direct_refresh` to refresh variables over streams/sockets instead of via fetch
- Load json if variable path suffix ends in .json or .geojson
- Get podman user id to set file owner
- Reduce memory consumption for massive batch lists
- Expose environment variable to control worker count for massive batch lists
- Update generated podman container image name to include localhost prefix

# 0.8
- Start from scratch
- Define AddProjectScript, ChangeProjectScript, SeeProjectScript
- Define AddToolScript, SeeToolScript
- Support reports
- Parallelize report and result automations using ThreadPoolExecutor

# 0.7
- Add `memory_level`, `processor_level` to work script
- Remove redundant calls to `data_type.load`
- Render `run_tool_json` errors in form
- Replace setup script with support for setup.sh in work script
- Replace `show_standard_output`, `show_standard_error` with `show_raw_output`
- Support inline default values in tool definition e.g. {--x} and {--x 1}
- Use hard links when available

# 0.6
- Accept markdown templates that lack titles
- Add work script
- Expand support for DataType.parse, DataType.render
- Handle empty arguments properly
- Rearrange result folder
- Recognize variable name and variable help in markdown templates

# 0.5
- Serve Python Jupyter Notebooks
- Support Python 3
- Support Unicode
- Support Windows

# 0.4
- Add tool scaffold
- Support data types that require extra stylesheets, scripts, api keys
- Make result files available from server
- Use DataTypeError to detect `data_type` errors
- Use DataType classmethods without instantiation

# 0.3
- Validate standard outputs and standard errors against data types
- Support popovers via help in tool definition

# 0.2
- Support data type plugins
- Add setup script

# 0.1
- Add run script
- Add serve script
