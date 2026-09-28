import base from "@nirnoy/config/eslint";

// Library package: hooks and components live together; Fast Refresh boundaries are an app concern.
export default [...base, { rules: { "react-refresh/only-export-components": "off" } }];
