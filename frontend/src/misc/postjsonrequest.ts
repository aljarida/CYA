const postJsonRequest = async (url: string, body: object) => {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });

  const data = await response.json().catch(() => {});

  return {
    ok: response.ok,
    status: response.status,
    data: data
  };
};

export default postJsonRequest;