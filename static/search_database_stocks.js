$(document).ready(function () {
    $(".select2").select2({
        width: "resolve",
    });

    var Symbol = function (name, symbol) {
        this.name = name;
        this.symbol = symbol;
    };

    var viewModel = {
        availableSymbols: ko.observableArray([]),
        selectedSymbol: ko.observable(), // Nothing selected by default
        quote: ko.observable(),
        error: ko.observable(),
        fetchSymbols: function (text) {

            $.getJSON("/symbols/" + text, function (json) {
                console.log("Loaded data:", json);
                viewModel.availableSymbols.removeAll();

                if (Array.isArray(json)) {
                    $.each(json, function (index, item) {
                        console.log("Adding: ", item);
                        console.log("to:", viewModel.availableSymbols());
                        console.log(viewModel.availableSymbols().length);
                        viewModel.availableSymbols.push(
                        new Symbol(item.name, item.symbol)
                        );
                    });
                } else {
                    viewModel.availableSymbols.push(json.name, json.symbol);
                }
            });
        },
        fetchQuote: function () {
            $.ajax({
                type: "POST",
                url: "/quote/" + viewModel.selectedSymbol(),
                crossDomain: true,
                headers: {
                    "Content-Type": "application/json",
                },
                dataType: "json", // json data
                success: function (result) {
                console.log("success");
                console.log(result);
                viewModel.quote(result);
                viewModel.error(null);
                },
                error: function (xhr, resp, text) {
                viewModel.quote(null);
                viewModel.error("Please select a correct stock.");
                },
            });
        },
        preLoad: function () {
            $.getJSON("/symbols/all", function (json) {});
        },
    };
    viewModel.preLoad();
    ko.applyBindings(viewModel);
    
    //Load initial symbols
    $(document).on("input", "input.select2-search__field", function () {
        var dInput = this.value;
        if (dInput.length > 1) {
            setTimeout(() => {
                viewModel.fetchSymbols(dInput);
            }, 400);

        console.log(viewModel.availableSymbols());
        }
    });

    viewModel.selectedSymbol.subscribe( function (newValue) {
        viewModel.fetchQuote();
    });
});