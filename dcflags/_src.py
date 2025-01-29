import csv
import os
import sys
import types
from typing import (
    Any,
    Callable,
    cast,
    Type,
    TypeVar,
)
import argparse
import dataclasses
import typing


TRUE = ("y", "yes", "t", "true", "on", "1")
FALSE = ("n", "no", "f", "false", "off", "0")


T = TypeVar("T")


class WrappedDefault:
    """Wraps default values, allowing printing
    of its value in help messages while
    indicating that the user did not
    supply a new value on the command line."""

    def __init__(
        self,
        value,
    ) -> None:
        self.value = value

    def __str__(
        self,
    ) -> str:
        return str(self.value)

    def __repr__(
        self,
    ) -> str:
        return repr(self.value)


def as_env_var(
    name: str,
    prefix: str,
) -> str:
    return f"{prefix}{name.upper()}"


def as_cmd_arg(
    name: str,
    underscore_to_dash: bool,
) -> str:
    if not underscore_to_dash:
        return name
    return name.replace("_", "-")


def parse(
    config_type: Type[T],
    env_prefix: str = "",
    underscore_to_dash: bool = True,
    argv=None,
    *args,
    **kwargs,
) -> T:
    """Instantiate a dataclass from cmd/env arguments.

    Each field of the dataclass can be assigned
    a value through command line arguments or
    environmental variables.

    Values are converted to their respective field's type.

    The environmental variable name for each respective
    field is the field's name uppercased.

    Priority is given to values in the following order,
    from the highest priority to the lowest priority:
    1. command line arguments
    2. environmental arguments
    3. default value of the field

    An error is raised if the value of an argument can not
    be converted to its type or if an argument that was not
    given does not have a default value.

    Fields must be of a type with a constructor that can take
    a single string as input.

    Default factories are never called unless the argument is
    missing (does not show up in help messages for example).

    Booleans are evaluated by matching (case insensitive) against
    the set of true strings ("y", "yes", "t", "true", "on", "1")
    and the set of false strings ("n", "no", "f", "false", "off", "0").
    It is considered an error if neither matches.

    Errors result in a usage string being printed as well as the error.
    The application is then stopped with an exit code of 1.

    Arguments:
        config_type: The config class to initialize. Must be a dataclass.
        env_prefix: Prefix to use for environmental variable names.
        underscore_to_dash: Replaces underscores with dashes for
            command line argument names.
        argv: Command line arguments. If `None`, `sys.argv` is used.
        *args: Positional arguments for `argparse.ArgumentParser`.
        **kwargs: Keyword arguments for `argparse.ArgumentParser`.
    Returns:
        An instance of the given config class.
    """
    if not dataclasses.is_dataclass(config_type):
        raise TypeError("the config type must be a dataclass")
    fields = dataclasses.fields(config_type)

    # add fields as command line arguments to the arg parser
    parser = argparse.ArgumentParser(*args, **kwargs)
    for field in fields:
        parser_kwargs: dict = {}
        help = (
            f"type: {getattr(field.type, '__name__', repr(field.type))}, "
            f"env: ${as_env_var(field.name, env_prefix)}"
        )
        if field.default is not dataclasses.MISSING:
            parser_kwargs["default"] = WrappedDefault(field.default)
            help += ", default: %(default)s"
        if field.type is bool:
            parser_kwargs["nargs"] = "?"
            parser_kwargs["const"] = True
        if _is_list(field.type):
            t = Any
            args = typing.get_args(field.type)
            if len(args) > 1:
                raise ValueError(f"invalid list type: {field.type}")
            if len(args) == 1:
                t = args[0]
            parser_kwargs["nargs"] = "*"
            help = (
                f"type: list of {getattr(t, '__name__', repr(t))}, "
                f"env: ${as_env_var(field.name, env_prefix)}"
            )
        parser.add_argument(
            "--" + as_cmd_arg(field.name, underscore_to_dash),
            help=help,
            **parser_kwargs,
        )

    # collect values from command line and env vars
    parsed_args = parser.parse_args(argv)
    config: dict = {}
    missing = []
    for field in fields:
        # command line arg
        value = getattr(parsed_args, field.name)
        if value is not None and not isinstance(value, WrappedDefault):
            if field.type is bool and isinstance(value, bool):
                config[field.name] = value
            else:
                config[field.name] = _to_type(field.type, value)
            continue

        # env var
        value = os.environ.get(
            as_env_var(field.name, env_prefix),
            None,
        )
        if value is not None:
            if _is_list(field.type):
                try:
                    value = list(csv.reader([value]))[0]
                except Exception:
                    parser.print_usage()
                    print(
                        f"{parser.prog or sys.argv[0]}: error: argument "
                        f"${as_env_var(field.name, env_prefix)}: invalid"
                    )
                    sys.exit(1)
            try:
                config[field.name] = _to_type(field.type, value)
            except Exception:
                parser.print_usage()
                print(
                    f"{parser.prog or sys.argv[0]}: error: argument "
                    f"${as_env_var(field.name, env_prefix)}: invalid "
                    f"{getattr(field.type, '__name__', repr(field.type))} "
                    f"value: '{value}'"
                )
                sys.exit(1)
            continue

        # default value
        if field.default is not dataclasses.MISSING:
            value = field.default
        elif field.default_factory is not dataclasses.MISSING:
            value = field.default_factory()
        else:
            missing.append(
                f"--{as_cmd_arg(field.name, underscore_to_dash)}/"
                f"${as_env_var(field.name, env_prefix)}",
            )
            continue
        config[field.name] = value
    if missing:
        parser.print_usage()
        print(
            f"{parser.prog or sys.argv[0]}: error: the following "
            f"arguments are required: {', '.join(missing)}"
        )
        sys.exit(1)
    return cast(T, config_type(**config))


def _to_type(t: Type[T], v: Any, depth: int = 0) -> T:
    if _is_none(t):
        if not v:
            return typing.cast(T, None)
        if str(v).lower() in ("none", "null"):
            return typing.cast(T, None)
        raise ValueError(f"invalid None value: '{v}'")
    if t is Any:
        return v
    if t is bool:
        if str(v).lower() in TRUE:
            return typing.cast(T, True)
        elif str(v).lower() in FALSE:
            return typing.cast(T, False)
        raise ValueError(f"invalid bool value: '{v}'")
    if _is_union(t):
        vv = None
        is_optional = False
        for t_ in typing.get_args(t):
            if _is_none(t_):
                is_optional = True
                continue
            try:
                return _to_type(t_, v)
            except Exception:
                pass
        if vv is None and not is_optional:
            raise ValueError(f"could not convert '{v}' to {t}")
        return typing.cast(T, vv)
    if _is_list(t):
        if depth > 0:
            raise ValueError(f"nested lists are not supported: {t}")
        tt = Any
        args = typing.get_args(t)
        if len(args) > 1:
            raise ValueError(f"invalid list type: {v}")
        if len(args) == 1:
            tt = args[0]
        return typing.cast(
            T,
            [_to_type(typing.cast(Type[T], tt), _v, depth + 1) for _v in v],
        )
    if dataclasses.is_dataclass(t):
        raise ValueError("nested dataclasses are not supported")
    return typing.cast(Callable, t)(v)


def _is_list(t: Any) -> bool:
    return (
        t is list or typing.get_origin(t) is list or typing.get_origin(t) is typing.List
    )


def _is_union(t: Any) -> bool:
    T = typing.cast(Any, getattr(types, "UnionType", None))
    if t is typing.Union:
        return True
    if isinstance(t, T):
        return True
    if typing.get_origin(t) is typing.Union:
        return True
    return isinstance(typing.get_origin(t), T)


def _is_none(t: Any) -> bool:
    return t is None or t is type(None)  # noqa: E721
