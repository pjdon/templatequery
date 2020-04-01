# Template Query

Provides an easy and readable way to create formattable template query strings with placeholders for psycopg2. Instead of wrapping arguments with `psycopg2.sql` classes (e.g. `Literal`, `Identifier`) the expected class can be written inside the query.

**Quick Example:**

```python
>>> TemplateQuery('SELECT * FROM {table@Q} WHERE {@I} {@S} {value@L}').format(
...    'column_name', '>=', table='public.my_table', value=100
... ).as_string(conn)

'SELECT * FROM "public"."my_table" WHERE "column_name" >= 100'
```

## Installation

This package requires [`psycopg2`](https://pypi.org/project/psycopg2/) and can be installed using `pip` to download it from [PyPI](https://pypi.org/project/templatequery/):

```bash
$ pip install templatequery
```

or using `setup.py` if you have downloaded the source package locally:

```bash
$ python setup.py build
$ sudo python setup.py install
```

## Usage

In psycopg2, variables can be inserted into queries using `%s` placeholders and supplying arguments to `cursor.execute` but this does not allow for identifier arguments such as table or columns names. The alternative is to use [`psycopg2.sql.SQL.format`](https://www.psycopg.org/docs/sql.html#psycopg2.sql.SQL.format) but this requires arguments to be converted into `Composable` objects such as  `Literal` or `Identifier`. 

The `TemplateQuery` class allows this conversion to be specified inside the query and applied to the formatting arguments automatically.

Normally placeholders are written as `{}` for positional arguments and `{key_name}` for keyword arguments.  `TemplateQuery` allows for additional placeholders of the form `{key_name@X}`, where `key_name` is optional and `X` is one of the following formats which applies to the relevant argument a class from `psycopg2.sql`:

* `S`  (wraps with `SQL`) raw query snippet with no escaping **!! beware of SQL injection !!**
* `I` (wraps with `Identifier`) identifier representing names of database objects
* `P` (wraps with `Placeholder`) %s style placeholder whose value can be added later

An additional form `Q` can be used to separate qualified names that are dot-separated, such as `"schema.table"`, into a `Composed` of individual `Identifier` objects joined by `SQL('.')` . Supplying a tuple of identifiers and using the `I` form will achieve the same result when using `psycopg2 >= 2.8`

## Example Script

```python
from psycopg2 import connect
from psycopg2.extras import execute_values
from templatequery import TemplateQuery
from random import randint

# example database configuration
connection_details = dict(
    host='localhost', dbname='test', user='postgres', password='password'
)

# example table containing items
params = dict(
    table='public.item',
    category='brand',
    value='price_cents',
)

# queries
query_create = TemplateQuery(
    "DROP TABLE IF EXISTS {table@Q}; "
    "CREATE TABLE {table@Q} ("
    "id bigserial, "
    "{category@I} varchar, "
    "{value@I} bigint);"
)

query_insert = TemplateQuery(
    "INSERT INTO {table@Q} ({category@I}, {value@I}) "
    "VALUES %s"
)

query_analyze = TemplateQuery(
    "SELECT "
    "{category@I}, AVG({value@I}) {avg_value@I}"
    "FROM {table@Q}"
    "GROUP BY {category@I}"
    "ORDER BY {avg_value@I}"
)

# connect to postgreSQL using a psycopg2 connection
with connect(**connection_details) as conn:
    cursor = conn.cursor()

    # create table
    cursor.execute(query_create.format(**params))

    # insert data
    # generate test data for columns (brand, price)
    # where a higher value gives a character closer to A
    data = []
    for _ in range(1000):
        score = randint(0, 5)
        data.append(('FEDCBA'[score], (randint(1, 10000) * (score + 1))))

    execute_values(cursor, query_insert.format(**params), data)

    conn.commit()

    # analyze average prices per category (brand)
    cursor.execute(
        query_analyze.format(
            **params,
            avg_value='avg_' + params['value']
        )
    )
    result = cursor.fetchall()
    
```

```python
>>> result
[
    ('F', Decimal('4975.8218390804597701')),
    ('E', Decimal('10353.853658536585')),
    ('D', Decimal('15447.445714285714')),
    ('C', Decimal('21370.236024844720')),
    ('B', Decimal('25997.774566473988')),
    ('A', Decimal('31847.215686274510'))
]
```



