import React from "react"
import PropTypes from "prop-types"
import clsx from "clsx"

const Button = ({ variant = "default", className, children, ...props }) => {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-md border font-medium focus:outline-none focus:ring-2 focus:ring-offset-2",
        {
          "bg-blue-500 text-white border-transparent hover:bg-blue-600": variant === "default",
          "bg-white text-gray-700 border-gray-300 hover:bg-gray-50": variant === "outline",
        },
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
}

Button.propTypes = {
  variant: PropTypes.oneOf(["default", "outline"]),
  className: PropTypes.string,
  children: PropTypes.node.isRequired,
}

export default Button
