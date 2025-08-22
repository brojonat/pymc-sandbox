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

Assume you're counting events per unit time. Estimate the underlying rate. Now assume you have many cohorts that produce/emit a variety of events, each with some underlying rate. This system will model the underlying rate for each cohort and event type and then allow you to compare. It does this dynamically as you add observed data points.
