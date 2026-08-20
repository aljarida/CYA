export type ApiResult<T> = {
  ok: boolean;
  status: number;
  data: T;
};

function networkErrorResult<T>(operation: string, error: unknown): ApiResult<T> {
  const detail = error instanceof Error ? error.message : String(error);
  return {
    ok: false,
    status: 0,
    data: {
      sender: 'error',
      content: `${operation} failed: could not reach the backend at localhost:3000. ${detail}`,
    } as T,
  };
}

export async function getJson<T>(
  url: string,
  params: Record<string, string | number> = {},
): Promise<ApiResult<T>> {
  const queryString = new URLSearchParams(
    Object.entries(params).reduce((acc, [key, value]) => {
      acc[key] = String(value);
      return acc;
    }, {} as Record<string, string>),
  ).toString();

  const fullUrl = queryString ? `${url}?${queryString}` : url;

  let response: Response;
  try {
    response = await fetch(fullUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
  } catch (error) {
    return networkErrorResult<T>('Request', error);
  }

  const data = await response.json().catch(() => undefined);

  return {
    ok: response.ok,
    status: response.status,
    data,
  };
}

export async function postJson<T>(url: string, body: object): Promise<ApiResult<T>> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
  } catch (error) {
    return networkErrorResult<T>('Request', error);
  }

  const data = await response.json().catch(() => undefined);

  return {
    ok: response.ok,
    status: response.status,
    data,
  };
}
