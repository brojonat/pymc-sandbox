# data-interface

We use [Ibis](https://ibis-project.org/why) to interface with the DB; this makes this database agnostic.

This approach provides a powerful layer of abstraction over the underlying data store. Ibis allows us to write our data queries using a consistent, expressive Python DataFrame API, which Ibis then translates into optimized SQL specific to the connected backend (like DuckDB or PostgreSQL). The key benefit is portability: we can develop our application with an embedded database like DuckDB and later switch to a production-grade database by changing only the connection details, without rewriting any of our data access logic. This keeps our code clean, maintainable, and independent of the specific database technology while still leveraging the full performance of the underlying engine.

See the following API documentation for reference:

- [Table expressions API](https://ibis-project.org/reference/expression-tables)

  - This is the core of Ibis, defining operations that transform entire tables of data. It includes fundamental verbs like `select`, `filter`, `mutate`, `group_by`, `agg`, `join`, and `order_by`. These methods are chainable and allow you to build complex, readable queries that Ibis translates into efficient SQL or other backend code.

- [Selectors API](https://ibis-project.org/reference/selectors)

  - Selectors provide a powerful way to choose columns based on their name, data type, or regular expressions. They are used within other table expressions like `select` and `mutate` to programmatically apply operations to multiple columns at once. This avoids repetitive code and makes data wrangling more maintainable.

- [Generic expressions API](https://ibis-project.org/reference/expression-generic)

  - This API covers operations that apply to columns of any type. Key functions include casting data types (`.cast()`), handling null values (`.isnull()`, `.fillna()`), and implementing conditional logic with `case()` statements or the `.ifelse()` method. These are the building blocks for data cleaning and transformation.

- [Numeric expressions API](https://ibis-project.org/reference/expression-numeric)

  - This API provides a comprehensive set of mathematical and statistical functions for numeric columns. It includes everything from basic arithmetic and rounding to more advanced operations like logarithms, exponentiation, and aggregations such as `sum()`, `mean()`, `std()`, and `var()`. It is essential for quantitative analysis.

- [String expressions API](https://ibis-project.org/reference/expression-string)

  - For columns containing text data, this API offers a wide range of manipulation functions. You can perform slicing, concatenation, case conversion, whitespace stripping, and powerful pattern matching using regular expressions. These tools are critical for cleaning and feature engineering with text.

- [Temporal expressions API](https://ibis-project.org/reference/expression-temporal)

  - This API is designed for working with date, time, and timestamp columns. It allows you to extract individual components (like year, month, or hour), perform arithmetic with time intervals, and format temporal values into strings. It is fundamental for any time-series analysis.

- [Collection expressions API](https://ibis-project.org/reference/expression-collection)

  - This API provides functions for working with array and map data types, which are common in modern data backends. Operations include getting the length of a collection, accessing elements by index or key, and unnesting arrays into a flat table structure.

- [JSON expressions API](https://ibis-project.org/reference/expression-json)
  - For columns containing JSON data, this API enables you to extract nested values using path expressions. You can navigate into JSON objects and arrays to pull out specific fields for use in your analysis. This is crucial for working with semi-structured data.
