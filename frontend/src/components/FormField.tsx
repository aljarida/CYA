import type { FormFieldProps } from "../misc/types";

function FormField({
    id, 
    name, 
    label, 
    type = "text", 
    value, 
    onChange, 
    placeholder, 
    required = false,
    isTextarea = false 
}: FormFieldProps) {
  return (
    <div>
        <label htmlFor={id} className="block text-neutral-300 mb-1">
        {label}
        {required && <span className="text-red-400">*</span>}
        </label>
        {isTextarea ? (
        <textarea
            id={id}
            name={name}
            value={value}
            onChange={onChange}
            className="w-full p-3 bg-neutral-800/80 backdrop-blur-sm text-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-500 placeholder-neutral-500 h-20 border border-neutral-700/50"
            placeholder={placeholder}
        />
        ) : (
        <input
            id={id}
            name={name}
            type={type}
            value={value}
            onChange={onChange}
            className="w-full p-3 bg-neutral-800/80 backdrop-blur-sm text-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-500 placeholder-neutral-500 border border-neutral-700/50"
            placeholder={placeholder}
        />
        )}
    </div>
)};

export default FormField;