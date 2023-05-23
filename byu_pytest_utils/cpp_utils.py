import logging
import subprocess as sp


def compile_cpp(*input_files, flags=['-Wall', '-std=c++17'], output_exec=None, compiler='g++'):
    command = ' '.join(
        [compiler, *flags, *([] if output_exec is None else ['-o', output_exec]), *input_files])
    proc = sp.run(command, stdout=sp.PIPE,
                  stderr=sp.STDOUT, shell=True, text=True)

    if proc.returncode != 0:
        raise Exception(f'"{command}" failed:\n{proc.stdout}')

    if proc.stdout:
        logging.warning(f'"{command}" gave output:\n{proc.stdout}')

    return './a.out' if output_exec is None else f'./{output_exec}'
