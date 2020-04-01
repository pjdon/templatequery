# -*- coding: utf-8 -*-
"""
Unit tests for templatequery
"""

from psycopg2.sql import Composed, SQL, Identifier, Literal, Placeholder
from unittest import TestCase, main

# must have template_query in sources root
from template_query import TemplateQuery


def composed(*args):
    """Simpler wrapper over Composed"""
    return Composed(args)


# assert that marker is as expected
assert TemplateQuery._placeholder_marker == '@'


class TemplateQueryTests(TestCase):
    def test_simple_kwarg_formatted(self):
        """All formats as keyword argument"""
        foo_val = 'bar'

        subtests = [
            ['{foo@S}', SQL],
            ['{foo@I}', Identifier],
            ['{foo@L}', Literal],
            ['{foo@P}', Placeholder]
        ]

        for p, f in subtests:
            with self.subTest(placeholder=p, formatter=f):
                tq = TemplateQuery(p)
                actual = tq.format(foo=foo_val)
                expected = composed(f(foo_val))
                self.assertEqual(actual, expected)

        p = '{foo@Q}'

        with self.subTest('schema.table identifier'):
            tq = TemplateQuery(p)
            actual = tq.format(foo="schema.table")
            expected = composed(
                Identifier('schema')
                + SQL('.')
                + Identifier('table')
            )
            self.assertEqual(actual, expected)

    def test_simple_posn_arg_formatted(self):
        """All formats as positional argument"""
        foo_val = 'bar'

        subtests = [
            ['{@S}', SQL],
            ['{@I}', Identifier],
            ['{@L}', Literal],
            ['{@P}', Placeholder]
        ]

        for p, f in subtests:
            with self.subTest(placeholder=p, formatter=f):
                tq = TemplateQuery(p)
                actual = tq.format(foo_val)
                expected = composed(f(foo_val))
                self.assertEqual(actual, expected)

        p = '{@Q}'

        with self.subTest('schema.table identifier'):
            tq = TemplateQuery(p)
            actual = tq.format("schema.table")
            expected = composed(
                Identifier('schema')
                + SQL('.')
                + Identifier('table')
            )
            self.assertEqual(actual, expected)

    def test_empty_query(self):
        """Empty query string"""
        actual = TemplateQuery('').format()
        expected = composed()
        self.assertEqual(actual, expected)

    def test_edge_case_placeholders(self):
        """Edge case placeholders that can fit on one query"""

        tq = TemplateQuery(
            "{} {foo} {bar@I} {bar@S} {bar@Q} {kyt@@S} {@I} {@} {@@} "
            "{tek@} {nol@@}"
        )

        actual = tq.format(
            Literal('a'),
            'c',
            **{
                'foo': Literal('b'),
                'bar': 'schema.table',
                'kyt@': 'apple.orange',
                '@': Identifier('banana'),
                '@@': SQL('mango'),
                'tek@': SQL('tangerine'),
                'nol@@': Literal('avacado')
            }
        )
        expected = composed(
            Literal('a'), SQL(' '), Literal('b'), SQL(' '),
            Identifier('schema.table'), SQL(' '), SQL('schema.table'), SQL(' '),
            composed(Identifier('schema'), SQL('.'), Identifier('table')),
            SQL(' '), SQL('apple.orange'), SQL(' '), Identifier('c'), SQL(' '),
            Identifier('banana'), SQL(' '), SQL('mango'), SQL(' '),
            SQL('tangerine'), SQL(' '), Literal('avacado')
        )

        self.assertEqual(actual, expected)

    def test_missing_posn_args(self):
        """Not enough positional arguments"""

        with self.assertRaises(IndexError):
            TemplateQuery("{}{@L}{foo@L}").format(
                'kyt', foo='bar'
            )

    def test_missing_kwargs(self):
        """Missing keyword argument"""

        with self.assertRaises(KeyError):
            TemplateQuery("{}{@L}{foo@L}").format(
                'sar', 'kyt'
            )


if __name__ == '__main__':
    main()
