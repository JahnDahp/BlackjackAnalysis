import React from "react";
import "../PlayStyles/Textbox.css";

interface Props {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  allowNegative?: boolean;
  onBlur?: () => void;
}

const Textbox = ({
  value,
  onChange,
  placeholder = "",
  allowNegative = false,
  onBlur,
}: Props) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const input = e.target.value;
    const regex = allowNegative ? /^-?\d*$/ : /^\d*$/;

    if (input === "" || regex.test(input)) {
      onChange(input);
    }
  };

  return (
    <input
      className="textbox"
      type="text"
      inputMode="numeric"
      pattern={allowNegative ? "-?[0-9]*" : "[0-9]*"}
      value={value}
      onChange={handleChange}
      placeholder={placeholder}
      onBlur={onBlur}
    />
  );
};

export default Textbox;
