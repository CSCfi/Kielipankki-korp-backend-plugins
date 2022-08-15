
# Korp backend plugins of the Language Bank of Finland (Kielipankki)

This independent branch of the [Kielipankki-korp-backend
repository](https://github.com/CSCfi/Kielipankki-korp-backend/)
contains various plugins for the Korp backend of the Language Bank of
Finland (Kielipankki).

Each plugin should be developed in a separate branch under the
`plugins/` branch namespace and then merged to `plugins/master` (or
possibly first to `plugins/dev`). The files of each plugin should be
under a separate subdirectory of `korpplugins`, forming a Python
module under the namespace package `korpplugins`.
