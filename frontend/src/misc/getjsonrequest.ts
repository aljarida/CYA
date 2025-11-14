const getJsonRequest = async (url: string, params: Record<string, string | number> = {}) => {
  const queryString = new URLSearchParams(
    Object.entries(params).reduce((acc, [key, value]) => {
      acc[key] = String(value);
      return acc;
    }, {} as Record<string, string>)
  ).toString();
  
  const fullUrl = queryString ? `${url}?${queryString}` : url;
  
  const response = await fetch(fullUrl, {
    method: "GET",
    headers: {
      "Content-Type": "application/json"
    }
  });

  const data = await response.json().catch(() => {});

  return {
    ok: response.ok,
    status: response.status,
    data: data
  };
};

export default getJsonRequest;

