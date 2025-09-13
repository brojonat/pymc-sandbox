# pymc-llm-dev

This project is a PyMC example that's developed with the assistance of an LLM to make sure we get the modeling syntax and whatnot correct.

## Use Cases

The idea is to provide a finite set of example use cases that leverage PyMC to answer interesting but simple data science problems. This is basically Bayesian Methods for Hackers extended.

### Bernoulli Trials

Let's assume we have some number of Bernoulli trials governed by some probability `p`. This could represent.

### AB(C) Test

This is the Bernoulli Trials example, but we have two (or more) observed streams of data and we want to estimate `p` for each of them.

### Multi Armed Bandits

### Poisson Cohort Rates

Assume you're observering individual events. Events may have arbitrary labels associated with them. Estimate the underlying rate (events per unit time). Now imagine you have many cohorts that produce/emit a variety of events, each with some fixed labels and some yet unknown underlying rate. This system will model the underlying rate for each cohort and event type and then allow you to compare them directly. That is the user experience: you select a data generation model and event label fields and we show the posterior for each parameter of the model. The starting example is the poisson model which will allow us to compare rates of different incidents.

TODO: the main issue with this at the moment is that all the cohort plots share the same x-axis; really there should be one global axis that shows the posteriors for all cohorts and then each cohort should have an independent x-axis plot that gives a sense of the width of the distribution.
