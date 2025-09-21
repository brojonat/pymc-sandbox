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

  getExperimentData(experimentName, params = {}) {
    const query = new URLSearchParams({
      experiment_name: experimentName,
      ...params,
    });
    return this._request(`/experiments/data?${query}`);
  }

  getPosterior(experimentName, params = {}) {
    const query = new URLSearchParams({
      ...params,
      experiment_name: experimentName,
    });
    return this._request(`/bernoulli/posterior?${query}`);
  }

  getABTestPosterior(experimentName, params = {}) {
    const query = new URLSearchParams({
      ...params,
      experiment_name: experimentName,
    });
    return this._request(`/ab-test/posterior?${query}`);
  }

  deleteExperiment(experimentName) {
    const query = new URLSearchParams({ experiment_name: experimentName });
    return this._request(`/experiments?${query}`, { method: "DELETE" });
  }

  recordEvent(experimentName, eventData) {
    const query = new URLSearchParams({ experiment_name: experimentName });
    return this._request(`/events?${query}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(eventData),
    });
  }
}

export const apiClient = new ApiClient();
