export function describeError(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg || "Invalid input").join("; ");
  return error?.message || "Something went wrong. Please try again.";
}
