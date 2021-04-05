$(document).ready(function () {
    $(".select2").select2({
        width: "resolve",
    });

    var Share = function (
        shares,
        shares_value,
        stock_name,
        stock_price,
        stock_symbol
    ) {
        this.shares = shares;
        this.shares_value = shares_value;
        this.stock_name = stock_name;
        this.stock_price = stock_price;
        this.stock_symbol = stock_symbol;
    };
    var viewModel = function () {
        var self = this;
        self.availableShares = ko.observableArray([]);
        self.fetchSymbols = function () {
            $.getJSON("/user/shares", function (json) {
            console.log("Loaded data:", json);
            if (Array.isArray(json)) {
                self.availableShares.removeAll();
                $.each(json, function (index, item) {
                console.log("Adding: ", item);
                console.log("to:", self.availableShares());
                console.log(self.availableShares().length);
                self.availableShares.push(
                    new Share(
                        item.shares,
                        item.shares_value,
                        item.stock_name,
                        item.stock_price,
                        item.stock_symbol
                    )
                );
            });
            } else {
                self.availableShares.removeAll();
                self.availableShares.push(
                    new Share(
                        json.shares,
                        json.shares_value,
                        json.stock_name,
                        json.stock_price,
                        json.stock_symbol
                    )
                );
            }
        });
    };

    self.fetchSymbols();
    self.selectedStockSymbol = ko.observable();
    self.selectedShare = ko.observable();
};
var model = new viewModel();
model.selectedStockSymbol.subscribe(function (newValue) {
console.log("Checking,", newValue);
console.log("Checking,", model.availableShares());
$.each(model.availableShares(), function (index, item) {
    console.log(item);
    if (newValue === item.stock_symbol) {
        console.log("its equal");
        model.selectedShare(item);
    }
});
});

    ko.applyBindings(model);
});