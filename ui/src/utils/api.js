import axios from 'axios';

// Create API client with CORS handling
const createCorsProxy = (baseUrl, jwtToken, useCorsProxy = false) => {
  // Use local proxy URL if CORS proxy is enabled
  const effectiveUrl = useCorsProxy 
    ? `/aws-api/search?target=${encodeURIComponent(baseUrl)}`
    : baseUrl;

  const instance = axios.create({
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${jwtToken}`
    }
  });

  // Add response interceptor to handle CORS errors with a friendly message
  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.message.includes('Network Error') || 
          (error.response && error.response.status === 0)) {
        console.error('CORS Error:', error);
        return Promise.reject({
          ...error,
          message: 'CORS Error: The API server is blocking requests from this origin. Try enabling the CORS proxy option.'
        });
      }
      return Promise.reject(error);
    }
  );

  return {
    search: async (query) => {
      try {
        return await instance.post(effectiveUrl, { query });
      } catch (error) {
        console.error('Error in search request:', error);
        throw error;
      }
    }
  };
};

export default createCorsProxy;