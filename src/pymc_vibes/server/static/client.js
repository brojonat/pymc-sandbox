class ApiClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
  }

  async _request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, options);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail || `HTTP error! status: ${response.status}`
      );
    }
    return response.json();
  }

  _buildQuery(params) {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (Array.isArray(value)) {
        value.forEach((v) => query.append(key, v));
      } else if (value !== undefined && value !== null) {
        query.append(key, value);
      }
    }
    return query.toString();
  }

  getExperimentData(experimentName, params = {}) {
    const allParams = { experiment_name: experimentName, ...params };
    const query = this._buildQuery(allParams);
    return this._request(`/experiments/data?${query}`);
  }

  getPosterior(experimentName, params = {}) {
    const allParams = { experiment_name: experimentName, ...params };
    const query = this._buildQuery(allParams);
    return this._request(`/bernoulli/posterior?${query}`);
  }

  getABTestPosterior(experimentName, params = {}) {
    const allParams = { experiment_name: experimentName, ...params };
    const query = this._buildQuery(allParams);
    return this._request(`/ab-test/posterior?${query}`);
  }

  getPoissonCohortsPosterior(experimentName, params = {}) {
    const allParams = { experiment_name: experimentName, ...params };
    const query = this._buildQuery(allParams);
    return this._request(`/poisson-cohorts/posterior?${query}`);
  }

  deleteExperiment(experimentName) {
    const query = this._buildQuery({ experiment_name: experimentName });
    return this._request(`/experiments?${query}`, { method: "DELETE" });
  }

  recordEvent(experimentName, eventData) {
    const query = this._buildQuery({ experiment_name: experimentName });
    return this._request(`/events?${query}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(eventData),
    });
  }
}

export const apiClient = new ApiClient();
