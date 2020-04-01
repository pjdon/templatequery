# -*- coding: utf-8 -*-
"""
Module for the `TemplateQuery` class which makes it easier compose SQL queries
for psycopg2 when specifying the sql object type of placeholders to prevent
SQL injection vulnerabilities.
"""

from typing import Union, Iterator, Match, List, Dict, Tuple, Any
from psycopg2.sql import Literal, Identifier, SQL, Placeholder, Composed
import re
from functools import reduce

# SQL syntax
_dot = '.'
_sql_dot = SQL(_dot)


def _dot_separated_identifier(
        qualified_name_string: str
) -> Union[Identifier, Composed]:
    """
    Converts the qualified name string `qualified_name_string` containing
    multiple dot-separated identifiers into a `Composed` object joining each
    subname formatted with `Identifier` with a sql dot, or a single `Identifier`
    if the name string contains no dots.
    """

    try:
        first_dot_index = qualified_name_string.index(_dot)
    except ValueError:
        # no split character so the whole string is the identifier
        return Identifier(qualified_name_string)

    schema = qualified_name_string[:first_dot_index]
    table = qualified_name_string[first_dot_index + 1:]

    return _sql_dot.join((
        Identifier(schema),
        Identifier(table)
    ))


class TemplateQuery:
    """Template query with psyopg2.sql placeholder embedded in the query string.

    Stores `query_text` as a template and replaces placeholders in the string
    with arguments that can be formatted based on tags inside the placeholder
    key.

    Formatting placeholders in `query_text` are written as `{key@X}` where
    `key` is the name of a keyword argument supplied to TemplateQuery.format
    and `X` is one of the following psyqcopg2.sql types:

        S: (SQL) raw query snippet with no escaping !!beware of SQL injection!!
        I: (Identifier) identifier representing names of database objects
        L: (Literal) value hardcoded into the query
        P: (Placeholder) %s style placeholder whose value can be added later
        Q: qualified name which is multiple dot-separated identifiers.
             In psycopg2 2.8, the same effect can be achieved by passing the
             identifiers as a `Tuple` of strings to the I: (Identifier)
             formatter

    If `X` is not one of the options above, the placeholder key will be treated
    as a regular placeholder, and the key should be present in the keyword
    args supplied to the `format` method.

    If `key` is not supplied, the placeholder draws its value from a positional
    argument. Regular placeholders (as used in `str.format`) are also supported,
    but the values passed to their arguments need to be `Composable` objects
    which are accepted by `psycopg2.sql.SQL.format`.

    Args:
        query_text: Query string that has placeholders which can be formatted.

    Examples:
         Simple schema-qualified table name and column value:
         >>> TemplateQuery('SELECT * FROM {@Q} WHERE foo={foo@L}').format(
         ...     'schema.table', foo='bar'
         ... )
         Composed([SQL('SELECT * FROM '), Composed([Identifier('schema'),
         SQL('.'), Identifier('table')]), SQL(' WHERE foo='), Literal('bar')])

         With regular arguments:
         >>> TemplateQuery('SELECT * FROM my_table WHERE foo{@S}{@L}').format(
         ...     '<', Literal(3)
         ... )
         Composed([SQL('SELECT * FROM my_table WHERE foo'), Literal(SQL('<')),
         Literal(3)])

    """
    # Acceptable placeholder formatting tags and the functions that are used to
    # format the arguments served to those placeholders.
    _placeholder_formatters = {
        'S': SQL,
        'I': Identifier,
        'L': Literal,
        'P': Placeholder,
        'Q': _dot_separated_identifier
    }
    # String that marks a placeholder key as one that needs to be formatted and
    # separated the key name from the format.
    _placeholder_marker = '@'

    # Regex search flags used in conjunction with `placeholder_pattern`.
    # braces doubled up to account for string formatting
    _placeholder_pattern = r"""
    \{{
        (?P<key>                      # full key name including marker and form
            (?P<subkey>               # key name excluding the marker and form
                [^\{{\}}]*?
            )
            (?:
                {marker}              # the marker character
                (?P<format>{formats}) # each possible form separated by |
            )?
        )
    \}}
    """
    # Regex search flags for the placeholder_pattern
    placeholder_search_flags = re.VERBOSE

    def __init__(self, query_text: str):
        self._matches = list(self._placeholder_matches_iterator(query_text))
        self._adjusted_query = self._adjusted_query_from_matches(
            query_text, self._matches
        )

    def _placeholder_matches_iterator(
            self,
            raw_query: str
    ) -> Iterator[Match]:
        """Returns iterator of all placeholder matches in `raw_query`"""

        possible_formats = list(self._placeholder_formatters.keys())
        formatted_pattern = self._placeholder_pattern.format(
            formats='|'.join(possible_formats),
            marker=self._placeholder_marker
        )
        compiled_pattern = re.compile(
            formatted_pattern,
            self.placeholder_search_flags
        )

        return compiled_pattern.finditer(raw_query)

    @staticmethod
    def _adjusted_query_from_matches(
            raw_query: str,
            matches: List[Match],
            replace_with='{}',

    ) -> str:
        """
        Returns `raw_query` with formatted placeholders (e.g. `{@I}`) replaced
        with regular placeholders `{}`.
        """

        # should be no multi-pass collisions since relevant matches
        # must have a format and target is an empty placeholder
        return reduce(
            lambda string, to_replace:
            string.replace(to_replace, replace_with),
            (
                m.group()
                for m in matches
                if m['format'] is not None and m['subkey'] == ''
            ),
            raw_query
        )

    def _process_format_args(
            self, *args, **kwargs
    ) -> Tuple[List, Dict[str, Any]]:
        """
        Returns `args` and `kwargs` with formatting applied to their values
        based on how their position or key matches with that of placeholder
        matches in the originally supplied `query_string`
        """

        # which positional argument to draw from next
        posn_arg_index = 0
        # total number of arguments
        posn_arg_count = len(args)

        # args to list so that items can be modified
        args = list(args)

        # kwarg keys that have a formatted placeholder
        formatted_kwarg_keys = set()
        # kwarg keys that have a regular placeholder
        unformatted_kwarg_keys = set()

        for match in self._matches:
            key = match['key']
            subkey = match['subkey']
            format_key = match['format']

            if format_key is None:
                # regular placeholder and the argument does not need to be
                # formatted

                if subkey == '':
                    # increment to next positional argument
                    posn_arg_index += 1

                else:
                    # keyword argument
                    unformatted_kwarg_keys.add(subkey)

            else:
                # special placeholder and the argument needs to be formatted

                # function used to format the argument based on placeholder
                # key format
                format_func = self._placeholder_formatters[format_key]

                if subkey == '':
                    # positional argument

                    if posn_arg_index >= posn_arg_count:
                        raise IndexError(
                            f"Positional argument placeholder at index "
                            f"{posn_arg_index} is larger than "
                            f"the number of positional arguments provided "
                            f"({posn_arg_count})."
                        )

                    # replace positional argument value with formatted value
                    args[posn_arg_index] = format_func(
                        args[posn_arg_index]
                    )

                    # increment to next positional arguments
                    posn_arg_index += 1

                else:
                    # keyword argument
                    if subkey not in kwargs:
                        raise KeyError(
                            f"'{subkey}' from placeholder '{key}' was not "
                            f"found in provided keyword arguments."
                        )
                    # apply the appropriate formatting to the keyword argument
                    # value and replace the original key with one that includes
                    # the format and marker

                    formatted_kwarg_keys.add(subkey)
                    kwargs[key] = format_func(kwargs[subkey])

        # remove kwargs that were only used formatted placeholders
        for kwarg_key in formatted_kwarg_keys - unformatted_kwarg_keys:
            del kwargs[kwarg_key]

        return args, kwargs

    def format(self, *args, **kwargs) -> Composed:
        """
        Returns a `psycopg2.sql.Composed` query by formatting the values of
        `args` and `kwargs` based on how their position or key matches with
        that of placeholders in the originally supplied `query_string`.

        Arguments that do not have a placeholder will be passed to the
        `psycopg.sql.SQL.format` method used to created the `Composed`
        query.

        Missing positional arguments will raise `IndexError` while missing
        keyword arguments will raise `KeyError`.

        See the class documentation for how to structure the query string
        and supply arguments to the `format` method properly.

        Args:
            args: positional arguments to format the query with
            kwargs: keyword arguments to format the query with

        Returns:
            A `Composed` query with the placeholders replaced by their
            associated values from *args and *kwargs.
        """

        new_args, new_kwargs = self._process_format_args(*args, **kwargs)

        return SQL(self._adjusted_query).format(*new_args, **new_kwargs)
