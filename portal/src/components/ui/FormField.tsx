import React from "react";
import { clsx } from "clsx";

interface FormFieldProps {
    label: string;
    error?: string;
    required?: boolean;
    hint?: string;
    children: React.ReactNode;
    className?: string;
}

export function FormField({
    label,
    error,
    required,
    hint,
    children,
    className,
}: FormFieldProps) {
    return (
        <div className={clsx("flex flex-col gap-1", className)}>
            <label className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                {label}
                {required && <span className="text-red-500 ml-1">*</span>}
            </label>
            {children}
            {hint && !error && <p className="text-xs text-gray-400">{hint}</p>}
            {error && <p className="text-xs text-red-600">{error}</p>}
        </div>
    );
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    error?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
    function Input({ error, className, ...props }, ref) {
        return (
            <input
                ref={ref}
                className={clsx(
                    "w-full px-3 py-2 text-sm border rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-teal-600 transition-colors",
                    error
                        ? "border-red-400"
                        : "border-gray-200 hover:border-gray-300",
                    className,
                )}
                {...props}
            />
        );
    },
);
Input.displayName = "Input";

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
    error?: boolean;
}

export function Select({ error, className, children, ...props }: SelectProps) {
    return (
        <select
            className={clsx(
                "w-full px-3 py-2 text-sm border rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-teal-600 transition-colors appearance-none",
                error
                    ? "border-red-400"
                    : "border-gray-200 hover:border-gray-300",
                className,
            )}
            {...props}
        >
            {children}
        </select>
    );
}

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
    error?: boolean;
}

export function Textarea({ error, className, ...props }: TextareaProps) {
    return (
        <textarea
            className={clsx(
                "w-full px-3 py-2 text-sm border rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-teal-600 transition-colors resize-none",
                error
                    ? "border-red-400"
                    : "border-gray-200 hover:border-gray-300",
                className,
            )}
            {...props}
        />
    );
}
