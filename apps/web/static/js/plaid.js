function linkAccountByPlaid(linkToken) {
    const handler = Plaid.create({
        token: linkToken,
        onSuccess: (public_token) => {
          htmx.ajax("POST", "/accounts/plaid", {
            values: { public_token },
            target: "#explorer-history",
            swap: "innerHTML"
          });
        }
    })

    handler.open();
}