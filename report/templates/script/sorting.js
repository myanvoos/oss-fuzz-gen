(function() {
    const tables = Array.from(document.querySelectorAll('table.sortable-table'));
    tables.forEach(tableElement => {
        const tableIdName = tableElement.id;
        const headers = Array.from(tableElement.querySelectorAll('th'));
        
        headers.forEach((th, colindex) => {
            th.addEventListener('click', () => {
                const sortAsc = th.dataset.sorted != "asc";
                const sortNumber = th.dataset.sortNumber != undefined;

                headers.forEach(innerTH => delete innerTH.dataset.sorted);
                th.dataset.sorted = sortAsc ? "asc" : "desc";

                const innerTables = Array.from(document.querySelectorAll('table.sortable-table'));
                innerTables.forEach(theTable => {
                    if (theTable.id == tableIdName) {
                        const tbody = theTable.querySelector('tbody');
                        const rows = Array.from(tbody.children);
                        rows.sort((a, b) => {
                            let [valueA, valueB] = [
                                a.children[colindex].dataset.sortValue, 
                                b.children[colindex].dataset.sortValue
                            ];
                            if (!sortAsc) [valueB, valueA] = [valueA, valueB];
                            return sortNumber ? Number(valueB) - Number(valueA) : valueA.localeCompare(valueB);
                        });
                        tbody.replaceChildren(...rows);
                        rows.forEach((r, i) => r.children[0].innerText = i);
                    }
                });
            });
        });
    });
})();