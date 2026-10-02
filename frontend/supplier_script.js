/* =========================================================
   SMART INVENTORY SUPPLIER PORTAL
   ADVANCED FRONTEND JAVASCRIPT
========================================================= */


/* =========================================================
   GLOBAL VARIABLES
========================================================= */

let toastTimer;

const body = document.body;

const sidebar = document.getElementById("sidebar");

const sidebarToggle =
    document.getElementById("sidebarToggle");

const mobileMenu =
    document.getElementById("mobileMenu");

const globalSearch =
    document.getElementById("globalSearch");


/* =========================================================
   PAGE NAVIGATION
========================================================= */

const navItems =
    document.querySelectorAll(".nav-item[data-page]");

const pages =
    document.querySelectorAll(".page");


function showPage(pageId) {

    pages.forEach(page => {

        page.classList.remove("active");

    });


    const target =
        document.getElementById(pageId);

    if (target) {

        target.classList.add("active");

    }


    navItems.forEach(item => {

        item.classList.remove("active");

        if (item.dataset.page === pageId) {

            item.classList.add("active");

        }

    });


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });


    if (window.innerWidth <= 800) {

        sidebar.classList.remove("mobile-open");

    }
}


navItems.forEach(item => {

    item.addEventListener("click", () => {

        showPage(item.dataset.page);

    });

});


/* =========================================================
   SIDEBAR COLLAPSE
========================================================= */

if (sidebarToggle) {

    sidebarToggle.addEventListener("click", () => {

        body.classList.toggle("sidebar-collapsed");

        const collapsed =
            body.classList.contains("sidebar-collapsed");

        localStorage.setItem(
            "sidebarCollapsed",
            collapsed
        );

    });

}


if (
    localStorage.getItem("sidebarCollapsed") === "true"
) {

    body.classList.add("sidebar-collapsed");

}


/* =========================================================
   MOBILE MENU
========================================================= */

if (mobileMenu) {

    mobileMenu.addEventListener("click", () => {

        sidebar.classList.toggle("mobile-open");

    });

}


/* =========================================================
   DARK MODE
========================================================= */

const themeToggle =
    document.getElementById("themeToggle");


function updateThemeIcon() {

    if (!themeToggle) return;

    const icon =
        themeToggle.querySelector("i");

    if (body.classList.contains("dark")) {

        icon.className =
            "fa-regular fa-sun";

    } else {

        icon.className =
            "fa-regular fa-moon";

    }
}


if (
    localStorage.getItem("supplierTheme") === "dark"
) {

    body.classList.add("dark");

}


updateThemeIcon();


if (themeToggle) {

    themeToggle.addEventListener("click", () => {

        body.classList.toggle("dark");

        localStorage.setItem(
            "supplierTheme",
            body.classList.contains("dark")
                ? "dark"
                : "light"
        );

        updateThemeIcon();

        showToast(
            "Theme updated",
            body.classList.contains("dark")
                ? "Dark mode enabled."
                : "Light mode enabled."
        );

    });

}


/* =========================================================
   GLOBAL SEARCH - CTRL + K
========================================================= */

document.addEventListener("keydown", event => {

    if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "k"
    ) {

        event.preventDefault();

        globalSearch.focus();

    }

});


if (globalSearch) {

    globalSearch.addEventListener(
        "keydown",
        event => {

            if (event.key === "Enter") {

                const query =
                    globalSearch.value
                        .trim()
                        .toLowerCase();

                if (!query) return;


                const mapping = {

                    request:
                        "requests",

                    quotation:
                        "quotations",

                    quote:
                        "quotations",

                    po:
                        "orders",

                    order:
                        "orders",

                    shipment:
                        "shipments",

                    inventory:
                        "inventory",

                    stock:
                        "inventory",

                    payment:
                        "payments",

                    invoice:
                        "payments",

                    document:
                        "documents",

                    analytics:
                        "analytics",

                    notification:
                        "notifications",

                    profile:
                        "profile"

                };


                let destination = null;


                Object.keys(mapping).forEach(keyword => {

                    if (
                        !destination &&
                        query.includes(keyword)
                    ) {

                        destination =
                            mapping[keyword];

                    }

                });


                if (destination) {

                    showPage(destination);

                    showToast(
                        "Search",
                        `Opening ${destination.replace(
                            "-", " "
                        )}.`
                    );

                } else {

                    showToast(
                        "Search",
                        `Searching for "${query}".`
                    );

                }

            }

        }
    );

}


/* =========================================================
   NOTIFICATION DRAWER
========================================================= */

const notificationButton =
    document.getElementById(
        "notificationButton"
    );

const notificationDrawer =
    document.getElementById(
        "notificationDrawer"
    );

const drawerOverlay =
    document.getElementById(
        "drawerOverlay"
    );

const closeDrawer =
    document.getElementById(
        "closeDrawer"
    );


function openNotificationDrawer() {

    notificationDrawer.classList.add("open");

    drawerOverlay.classList.add("show");

}


function closeNotificationDrawer() {

    notificationDrawer.classList.remove("open");

    drawerOverlay.classList.remove("show");

}


if (notificationButton) {

    notificationButton.addEventListener(
        "click",
        openNotificationDrawer
    );

}


if (closeDrawer) {

    closeDrawer.addEventListener(
        "click",
        closeNotificationDrawer
    );

}


if (drawerOverlay) {

    drawerOverlay.addEventListener(
        "click",
        closeNotificationDrawer
    );

}


/* =========================================================
   TOAST
========================================================= */

function showToast(
    title = "Success",
    message = "Action completed successfully."
) {

    const toast =
        document.getElementById("toast");

    const toastTitle =
        document.getElementById("toastTitle");

    const toastMessage =
        document.getElementById("toastMessage");


    toastTitle.textContent = title;

    toastMessage.textContent = message;

    toast.classList.add("show");


    clearTimeout(toastTimer);


    toastTimer = setTimeout(() => {

        toast.classList.remove("show");

    }, 3500);

}


function hideToast() {

    const toast =
        document.getElementById("toast");

    toast.classList.remove("show");

}


/* =========================================================
   REQUEST DETAILS MODAL
========================================================= */

const requestModal =
    document.getElementById("requestModal");


function openRequestDetails(
    id,
    product,
    qty,
    date,
    priority
) {

    document.getElementById(
        "requestModalTitle"
    ).textContent = id;


    document.getElementById(
        "requestModalProduct"
    ).textContent = product;


    document.getElementById(
        "detailQty"
    ).textContent = qty;


    document.getElementById(
        "detailDate"
    ).textContent = date;


    document.getElementById(
        "detailPriority"
    ).textContent = priority;


    requestModal.classList.add("show");

}


function closeRequestModal() {

    requestModal.classList.remove("show");

}


function rejectRequest() {

    closeRequestModal();

    showToast(
        "Request rejected",
        "The request has been marked for rejection."
    );

}


/* =========================================================
   QUOTATION MODAL
========================================================= */

const quotationModal =
    document.getElementById(
        "quotationModal"
    );


function openQuotationModal(
    requestId = "SR-2026-0148",
    product = "Industrial Bearings"
) {

    document.getElementById(
        "quoteRequestId"
    ).textContent = requestId;


    document.getElementById(
        "quoteProduct"
    ).textContent = product;


    quotationModal.classList.add("show");

    calculateQuotation();

}


function closeQuotationModal() {

    quotationModal.classList.remove("show");

}


/* =========================================================
   QUOTATION CALCULATOR
========================================================= */

const availableQty =
    document.getElementById("availableQty");

const unitPrice =
    document.getElementById("unitPrice");

const discount =
    document.getElementById("discount");

const gstRate =
    document.getElementById("gstRate");

const shipping =
    document.getElementById("shipping");


function money(value) {

    return "₹" + Number(value).toLocaleString(
        "en-IN",
        {
            maximumFractionDigits: 2
        }
    );

}


function calculateQuotation() {

    if (
        !availableQty ||
        !unitPrice ||
        !discount ||
        !gstRate ||
        !shipping
    ) return;


    const qty =
        Number(availableQty.value) || 0;

    const price =
        Number(unitPrice.value) || 0;

    const discountRate =
        Number(discount.value) || 0;

    const gst =
        Number(gstRate.value) || 0;

    const shippingAmount =
        Number(shipping.value) || 0;


    const subtotal =
        qty * price;


    const discountAmount =
        subtotal * discountRate / 100;


    const taxable =
        subtotal - discountAmount;


    const gstAmount =
        taxable * gst / 100;


    const total =
        taxable +
        gstAmount +
        shippingAmount;


    document.getElementById(
        "quoteSubtotal"
    ).textContent = money(subtotal);


    document.getElementById(
        "quoteDiscount"
    ).textContent =
        "− " + money(discountAmount);


    document.getElementById(
        "quoteGST"
    ).textContent =
        money(gstAmount);


    document.getElementById(
        "quoteShipping"
    ).textContent =
        money(shippingAmount);


    document.getElementById(
        "quoteTotal"
    ).textContent =
        money(total);

}


[
    availableQty,
    unitPrice,
    discount,
    gstRate,
    shipping
].forEach(input => {

    if (input) {

        input.addEventListener(
            "input",
            calculateQuotation
        );

        input.addEventListener(
            "change",
            calculateQuotation
        );

    }

});


/* =========================================================
   QUOTATION SUBMIT
========================================================= */

const quotationForm =
    document.getElementById(
        "quotationForm"
    );


if (quotationForm) {

    quotationForm.addEventListener(
        "submit",
        event => {

            event.preventDefault();


            const qty =
                Number(
                    availableQty.value
                );


            if (qty <= 0) {

                showToast(
                    "Invalid quantity",
                    "Available quantity must be greater than zero."
                );

                return;

            }


            closeQuotationModal();


            showToast(
                "Quotation submitted",
                "Your quotation has been submitted successfully."
            );


            quotationForm.reset();


            availableQty.value = 250;

            unitPrice.value = 750;

            discount.value = 0;

            gstRate.value = 18;

            shipping.value = 0;


            calculateQuotation();

        }
    );

}


function saveQuotationDraft() {

    closeQuotationModal();

    localStorage.setItem(
        "quotationDraftSaved",
        "true"
    );

    showToast(
        "Draft saved",
        "Quotation has been saved as a draft."
    );

}


/* =========================================================
   STOCK MODAL
========================================================= */

const stockModal =
    document.getElementById(
        "stockModal"
    );


function openStockModal(
    product = "Industrial Bearings"
) {

    document.getElementById(
        "stockProductName"
    ).textContent =
        product;


    document.getElementById(
        "stockProductInput"
    ).value =
        product;


    stockModal.classList.add("show");

}


function closeStockModal() {

    stockModal.classList.remove("show");

}


const stockForm =
    document.getElementById(
        "stockForm"
    );


if (stockForm) {

    stockForm.addEventListener(
        "submit",
        event => {

            event.preventDefault();

            closeStockModal();

            showToast(
                "Inventory updated",
                "Stock quantity has been updated successfully."
            );

        }
    );

}


/* =========================================================
   LOW STOCK FILTER
========================================================= */

function filterLowStock() {

    const cards =
        document.querySelectorAll(
            ".inventory-product-card"
        );


    cards.forEach(card => {

        if (
            card.classList.contains("low-stock") ||
            card.classList.contains("critical-stock")
        ) {

            card.style.display = "";

        } else {

            card.style.display = "none";

        }

    });


    showToast(
        "Low stock filter",
        "Showing products that need attention."
    );

}


/* =========================================================
   REQUEST SEARCH + FILTER
========================================================= */

const requestSearch =
    document.getElementById(
        "requestSearch"
    );

const requestStatusFilter =
    document.getElementById(
        "requestStatusFilter"
    );

const priorityFilter =
    document.getElementById(
        "priorityFilter"
    );


function filterRequests() {

    const query =
        requestSearch
            ? requestSearch.value
                .toLowerCase()
            : "";


    const status =
        requestStatusFilter
            ? requestStatusFilter.value
            : "all";


    const priority =
        priorityFilter
            ? priorityFilter.value
            : "all";


    const rows =
        document.querySelectorAll(
            "#requestTable tbody tr"
        );


    rows.forEach(row => {

        const text =
            row.textContent.toLowerCase();


        const rowStatus =
            row.dataset.status;


        const rowPriority =
            row.dataset.priority;


        const matchesSearch =
            !query ||
            text.includes(query);


        const matchesStatus =
            status === "all" ||
            rowStatus === status;


        const matchesPriority =
            priority === "all" ||
            rowPriority === priority;


        row.style.display =
            matchesSearch &&
            matchesStatus &&
            matchesPriority
                ? ""
                : "none";

    });

}


if (requestSearch) {

    requestSearch.addEventListener(
        "input",
        filterRequests
    );

}


if (requestStatusFilter) {

    requestStatusFilter.addEventListener(
        "change",
        filterRequests
    );

}


if (priorityFilter) {

    priorityFilter.addEventListener(
        "change",
        filterRequests
    );

}


/* =========================================================
   SELECT ALL REQUESTS
========================================================= */

const selectAllRequests =
    document.getElementById(
        "selectAllRequests"
    );


if (selectAllRequests) {

    selectAllRequests.addEventListener(
        "change",
        () => {

            document.querySelectorAll(
                ".row-check"
            ).forEach(check => {

                check.checked =
                    selectAllRequests.checked;

            });

            showToast(
                "Selection updated",
                "Request selection has been updated."
            );

        }
    );

}


/* =========================================================
   EXPORT TABLE TO CSV
========================================================= */

function exportTable(tableId) {

    let table;

    if (tableId === "dashboard") {

        table =
            document.querySelector(
                "#dashboard table"
            );

    } else {

        table =
            document.getElementById(tableId);

    }


    if (!table) {

        showToast(
            "Export",
            "No table available for export."
        );

        return;

    }


    const rows =
        [...table.querySelectorAll("tr")];


    const csv =
        rows.map(row => {

            const cells =
                [...row.querySelectorAll("th,td")];


            return cells.map(cell => {

                let text =
                    cell.innerText
                        .replace(/\n/g, " ")
                        .replace(/"/g, '""')
                        .trim();


                return `"${text}"`;

            }).join(",");

        }).join("\n");


    const blob =
        new Blob(
            [csv],
            {
                type: "text/csv;charset=utf-8;"
            }
        );


    const url =
        URL.createObjectURL(blob);


    const link =
        document.createElement("a");


    link.href = url;

    link.download =
        `smart-inventory-${Date.now()}.csv`;


    document.body.appendChild(link);

    link.click();

    link.remove();

    URL.revokeObjectURL(url);


    showToast(
        "Export completed",
        "CSV file has been downloaded."
    );

}


/* =========================================================
   COPY TRACKING NUMBER
========================================================= */

function copyTracking(number) {

    if (
        navigator.clipboard &&
        navigator.clipboard.writeText
    ) {

        navigator.clipboard.writeText(number)
            .then(() => {

                showToast(
                    "Copied",
                    `${number} copied to clipboard.`
                );

            });

    } else {

        showToast(
            "Tracking number",
            number
        );

    }

}


/* =========================================================
   MARK ALL NOTIFICATIONS READ
========================================================= */

const readAll =
    document.getElementById(
        "readAll"
    );


if (readAll) {

    readAll.addEventListener(
        "click",
        () => {

            document
                .querySelectorAll(
                    ".notification-row.unread"
                )
                .forEach(item => {

                    item.classList.remove(
                        "unread"
                    );

                    const dot =
                        item.querySelector(
                            ".unread-dot"
                        );

                    if (dot) {

                        dot.remove();

                    }

                });


            document
                .querySelectorAll(
                    ".drawer-notification.unread"
                )
                .forEach(item => {

                    item.classList.remove(
                        "unread"
                    );

                });


            document
                .querySelectorAll(
                    ".notification-dot"
                )
                .forEach(dot => {

                    dot.textContent = "0";

                    dot.style.display =
                        "none";

                });


            showToast(
                "Notifications cleared",
                "All notifications have been marked as read."
            );

        }
    );

}


/* =========================================================
   DOCUMENT FILTERS
========================================================= */

document
    .querySelectorAll(".document-filter")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                document
                    .querySelectorAll(
                        ".document-filter"
                    )
                    .forEach(btn => {

                        btn.classList.remove(
                            "active"
                        );

                    });


                button.classList.add("active");


                showToast(
                    "Document filter",
                    `${button.textContent.trim()} selected.`
                );

            }
        );

    });


/* =========================================================
   NOTIFICATION TABS
========================================================= */

document
    .querySelectorAll(".notification-tabs button")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                document
                    .querySelectorAll(
                        ".notification-tabs button"
                    )
                    .forEach(btn => {

                        btn.classList.remove(
                            "active"
                        );

                    });


                button.classList.add("active");

            }
        );

    });


/* =========================================================
   PROFILE SAVE
========================================================= */

const saveProfile =
    document.getElementById(
        "saveProfile"
    );


if (saveProfile) {

    saveProfile.addEventListener(
        "click",
        () => {

            const companyName =
                document.getElementById(
                    "companyName"
                );


            if (companyName) {

                localStorage.setItem(
                    "supplierCompanyName",
                    companyName.value
                );

            }


            showToast(
                "Profile saved",
                "Company information has been updated."
            );

        }
    );

}


/* =========================================================
   RESTORE PROFILE
========================================================= */

const savedCompanyName =
    localStorage.getItem(
        "supplierCompanyName"
    );


if (
    savedCompanyName &&
    document.getElementById("companyName")
) {

    document.getElementById(
        "companyName"
    ).value =
        savedCompanyName;

}


/* =========================================================
   LOGOUT
========================================================= */

const logoutBtn =
    document.getElementById(
        "logoutBtn"
    );


if (logoutBtn) {

    logoutBtn.addEventListener(
        "click",
        () => {

            const confirmLogout =
                confirm(
                    "Are you sure you want to sign out?"
                );


            if (confirmLogout) {

                showToast(
                    "Signed out",
                    "Demo logout completed."
                );

            }

        }
    );

}


/* =========================================================
   MODAL BACKDROP CLOSE
========================================================= */

document
    .querySelectorAll(".modal-overlay")
    .forEach(overlay => {

        overlay.addEventListener(
            "click",
            event => {

                if (
                    event.target === overlay
                ) {

                    overlay.classList.remove(
                        "show"
                    );

                }

            }
        );

    });


/* =========================================================
   ESCAPE KEY
========================================================= */

document.addEventListener(
    "keydown",
    event => {

        if (event.key !== "Escape") return;


        document
            .querySelectorAll(
                ".modal-overlay.show"
            )
            .forEach(modal => {

                modal.classList.remove(
                    "show"
                );

            });


        closeNotificationDrawer();

    }
);


/* =========================================================
   CHART FILTER DEMO
========================================================= */

const chartFilter =
    document.getElementById(
        "chartFilter"
    );


if (chartFilter) {

    chartFilter.addEventListener(
        "change",
        () => {

            showToast(
                "Chart updated",
                `${chartFilter.value} data selected.`
            );

        }
    );

}


/* =========================================================
   PERIOD FILTER
========================================================= */

document
    .querySelectorAll(".period-select")
    .forEach(select => {

        select.addEventListener(
            "change",
            () => {

                showToast(
                    "Analytics updated",
                    `${select.value} selected.`
                );

            }
        );

    });


/* =========================================================
   INITIALIZATION
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        calculateQuotation();

        console.log(
            "Smart Inventory Supplier Portal loaded successfully."
        );

    }
);