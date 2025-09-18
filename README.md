# pymc-llm-dev

This project is a PyMC example that's developed with the assistance of an LLM to make sure we get the modeling syntax and whatnot correct.

## Use Cases

The idea is to provide a finite set of example use cases that leverage PyMC to answer interesting but simple data science problems. This is basically Bayesian Methods for Hackers extended. From a high level, the API is structured around the idea that all these use cases involve starting an "experiment" and then submitting "events" to that experiment.

### Bernoulli Trials (TODO)

Let's assume we have some number of Bernoulli trials governed by some probability `p`. This could represent and experiment where users pick A or B.

### AB(C) Test (TODO)

This is like a click-through experiment. Users are presented with an opportunity to click-through or not (i.e., each interaction is a Bernoulli Trial). Each user is presented with 1 of N different "treatments" (one of which is the null treatment). This results in N observed streams of data and we want to estimate `p` for each of them. Ideally we can show this dynamically in the dashboard. The API is:

### Multi Armed Bandits (TODO)

This is a classic problem with a solution that is well described (I think) in Bayesian Methods for Hackers. Traditionally it is rather difficult, but with PyMC it's actually quite tractable. This is a great example of modeling expectation values.

### Poisson Cohort Rates

Assume you're observering individual events. Events may have arbitrary labels associated with them. Estimate the underlying rate (events per unit time). Now imagine you have many cohorts that produce/emit a variety of events, each with some fixed labels and some yet unknown underlying rate. This system will model the underlying rate for each cohort and event type and then allow you to compare them directly.
