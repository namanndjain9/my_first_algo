// Dashboard tabs.
// To add a new tab: create a component in this folder and add it to the list below.
import UserTab from "./UserTab.jsx";
import SignalsTab from "./SignalsTab.jsx";

export const tabs = [
  { id: "user", label: "User", component: UserTab },
  { id: "signals", label: "Signals", component: SignalsTab },
  // { id: "holdings", label: "Holdings", component: HoldingsTab },
];
