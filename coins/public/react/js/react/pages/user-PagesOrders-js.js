"use strict";
(self["webpackChunk"] = self["webpackChunk"] || []).push([["./react/pages/user-PagesOrders-js"],{

/***/ "./resources/react/pages/user/PagesOrders.js":
/*!***************************************************!*\
  !*** ./resources/react/pages/user/PagesOrders.js ***!
  \***************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-runtime */ "./node_modules/react/jsx-runtime.js");
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
/* harmony import */ var _components_user_css_responsive_scss__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../../components/user/css/responsive.scss */ "./resources/react/components/user/css/responsive.scss");
/* harmony import */ var react_router_dom__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! react-router-dom */ "./node_modules/react-router-dom/es/Link.js");
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }





function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _createSuper(Derived) { var hasNativeReflectConstruct = _isNativeReflectConstruct(); return function _createSuperInternal() { var Super = _getPrototypeOf(Derived), result; if (hasNativeReflectConstruct) { var NewTarget = _getPrototypeOf(this).constructor; result = Reflect.construct(Super, arguments, NewTarget); } else { result = Super.apply(this, arguments); } return _possibleConstructorReturn(this, result); }; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } else if (call !== void 0) { throw new TypeError("Derived constructors may only return object or undefined"); } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _isNativeReflectConstruct() { if (typeof Reflect === "undefined" || !Reflect.construct) return false; if (Reflect.construct.sham) return false; if (typeof Proxy === "function") return true; try { Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {})); return true; } catch (e) { return false; } }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }





var PagesHome = /*#__PURE__*/function (_Component) {
  _inherits(PagesHome, _Component);

  var _super = _createSuper(PagesHome);

  function PagesHome(props) {
    var _this;

    _classCallCheck(this, PagesHome);

    _this = _super.call(this, props);
    _this.state = {
      orders: []
    };
    return _this;
  }

  _createClass(PagesHome, [{
    key: "loadOrders",
    value: function loadOrders() {
      var _this2 = this;

      App.loading(true);
      axios({
        method: 'POST',
        url: '/user/pages/getOrders',
        dataType: 'json'
      }).then(function (response) {
        App.loading(false);
        response = response.data;

        if (response['result']) {
          _this2.setState({
            orders: response['data']
          });
        } else {
          error_handle(response);
        }
      })["catch"](function (error) {
        App.loading(false);
        console.log(error);
        error_handle(error.response);
      });
    }
  }, {
    key: "componentDidMount",
    value: function componentDidMount() {
      this.loadOrders();
    }
  }, {
    key: "render",
    value: function render() {
      if (this.state.orders.length == 0) {
        return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          className: "container box_padding",
          children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "alert alert-warning",
            role: "alert",
            children: "B\u1EA1n kh\xF4ng c\xF3 \u0111\u01A1n h\xE0ng n\xE0o"
          })
        });
      }

      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.Fragment, {
        children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          className: "container box_padding",
          children: this.state.orders.map(function (item) {
            var status = /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
              style: {
                color: 'red'
              },
              children: "\u0110\xE3 \u0110\u1EB7t H\xE0ng"
            });

            if (item[ORDER_STATUS] == ORDER_STATUS_PENDING) status = /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
              style: {
                color: 'orange'
              },
              children: "\u0110ang x\u1EED l\xFD"
            });
            if (item[ORDER_STATUS] == ORDER_STATUS_COMPLETED) status = /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
              style: {
                color: 'green'
              },
              children: "Ho\xE0n th\xE0nh"
            });
            if (item[ORDER_STATUS] == ORDER_STATUS_CANCEL) status = /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
              style: {
                color: 'gray'
              },
              children: "\u0110\xE3 h\u1EE7y"
            });
            return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(react_router_dom__WEBPACK_IMPORTED_MODULE_3__.default, {
              to: "/user/pages/product?id=".concat(item[ORDER_PID]),
              children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_shadow box_padding box_flex",
                style: {
                  marginBottom: 5
                },
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("i", {
                    className: "fa fa-shopping-cart",
                    style: {
                      fontSize: 42,
                      color: '#4CAF50',
                      marginRight: 15
                    }
                  })
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                  children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                    children: ["T\xEAn s\u1EA3n ph\u1EA9m: ", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("span", {
                      children: item[ORDER_PNAME]
                    })]
                  }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                    children: ["\u0110\u01A1n gi\xE1: ", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
                      children: formatNumber(item[ORDER_PPRICE])
                    })]
                  }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                    children: ["S\u1ED1 l\u01B0\u1EE3ng: ", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
                      children: item[ORDER_PNUMBER]
                    })]
                  }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                    className: "box_flex",
                    children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                      style: {
                        color: 'gray',
                        fontWeight: 'bold',
                        display: item[ORDER_VVALUE] == 0 ? 'none' : 'block',
                        textDecoration: 'line-through'
                      },
                      children: [formatNumber(Number(item[ORDER_PPRICE]) * Number(item[ORDER_PNUMBER])), "\xA0VN\u0110"]
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                      style: {
                        color: item[ORDER_VVALUE] == 0 ? 'red' : 'green',
                        fontWeight: 'bold',
                        marginLeft: 15
                      },
                      children: [formatNumber(Number(item[ORDER_PPRICE]) * Number(item[ORDER_PNUMBER]) - Number(item[ORDER_VVALUE])), "\xA0VN\u0110"]
                    })]
                  }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                    children: ["Tr\u1EA1ng th\xE1i: ", status]
                  })]
                })]
              })
            }, item[ORDER_ID]);
          })
        })
      });
    }
  }]);

  return PagesHome;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (PagesHome);

/***/ }),

/***/ "./resources/simulation/pages/user/PagesOrders.js":
/*!********************************************************!*\
  !*** ./resources/simulation/pages/user/PagesOrders.js ***!
  \********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-runtime */ "./node_modules/react/jsx-runtime.js");
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
/* harmony import */ var _components_user_css_responsive_scss__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../../components/user/css/responsive.scss */ "./resources/simulation/components/user/css/responsive.scss");
/* harmony import */ var react_router_dom__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! react-router-dom */ "./node_modules/react-router-dom/es/Link.js");
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }





function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _createSuper(Derived) { var hasNativeReflectConstruct = _isNativeReflectConstruct(); return function _createSuperInternal() { var Super = _getPrototypeOf(Derived), result; if (hasNativeReflectConstruct) { var NewTarget = _getPrototypeOf(this).constructor; result = Reflect.construct(Super, arguments, NewTarget); } else { result = Super.apply(this, arguments); } return _possibleConstructorReturn(this, result); }; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } else if (call !== void 0) { throw new TypeError("Derived constructors may only return object or undefined"); } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _isNativeReflectConstruct() { if (typeof Reflect === "undefined" || !Reflect.construct) return false; if (Reflect.construct.sham) return false; if (typeof Proxy === "function") return true; try { Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {})); return true; } catch (e) { return false; } }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }





var PagesHome = /*#__PURE__*/function (_Component) {
  _inherits(PagesHome, _Component);

  var _super = _createSuper(PagesHome);

  function PagesHome(props) {
    var _this;

    _classCallCheck(this, PagesHome);

    _this = _super.call(this, props);
    _this.state = {
      orders: []
    };
    return _this;
  }

  _createClass(PagesHome, [{
    key: "loadOrders",
    value: function loadOrders() {
      var _this2 = this;

      App.loading(true);
      axios({
        method: 'POST',
        url: '/user/pages/getOrders',
        dataType: 'json'
      }).then(function (response) {
        App.loading(false);
        response = response.data;

        if (response['result']) {
          _this2.setState({
            orders: response['data']
          });
        } else {
          error_handle(response);
        }
      })["catch"](function (error) {
        App.loading(false);
        console.log(error);
        error_handle(error.response);
      });
    }
  }, {
    key: "componentDidMount",
    value: function componentDidMount() {
      this.loadOrders();
    }
  }, {
    key: "render",
    value: function render() {
      if (this.state.orders.length == 0) {
        return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          className: "container box_padding",
          children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "alert alert-warning",
            role: "alert",
            children: "B\u1EA1n kh\xF4ng c\xF3 \u0111\u01A1n h\xE0ng n\xE0o"
          })
        });
      }

      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.Fragment, {
        children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          className: "container box_padding",
          children: this.state.orders.map(function (item) {
            var status = /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
              style: {
                color: 'red'
              },
              children: "\u0110\xE3 \u0110\u1EB7t H\xE0ng"
            });

            if (item[ORDER_STATUS] == ORDER_STATUS_PENDING) status = /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
              style: {
                color: 'orange'
              },
              children: "\u0110ang x\u1EED l\xFD"
            });
            if (item[ORDER_STATUS] == ORDER_STATUS_COMPLETED) status = /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
              style: {
                color: 'green'
              },
              children: "Ho\xE0n th\xE0nh"
            });
            if (item[ORDER_STATUS] == ORDER_STATUS_CANCEL) status = /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
              style: {
                color: 'gray'
              },
              children: "\u0110\xE3 h\u1EE7y"
            });
            return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(react_router_dom__WEBPACK_IMPORTED_MODULE_3__.default, {
              to: "/user/pages/product?id=".concat(item[ORDER_PID]),
              children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_shadow box_padding box_flex",
                style: {
                  marginBottom: 5
                },
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("i", {
                    className: "fa fa-shopping-cart",
                    style: {
                      fontSize: 42,
                      color: '#4CAF50',
                      marginRight: 15
                    }
                  })
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                  children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                    children: ["T\xEAn s\u1EA3n ph\u1EA9m: ", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("span", {
                      children: item[ORDER_PNAME]
                    })]
                  }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                    children: ["\u0110\u01A1n gi\xE1: ", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
                      children: formatNumber(item[ORDER_PPRICE])
                    })]
                  }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                    children: ["S\u1ED1 l\u01B0\u1EE3ng: ", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
                      children: item[ORDER_PNUMBER]
                    })]
                  }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                    className: "box_flex",
                    children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                      style: {
                        color: 'gray',
                        fontWeight: 'bold',
                        display: item[ORDER_VVALUE] == 0 ? 'none' : 'block',
                        textDecoration: 'line-through'
                      },
                      children: [formatNumber(Number(item[ORDER_PPRICE]) * Number(item[ORDER_PNUMBER])), "\xA0VN\u0110"]
                    }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                      style: {
                        color: item[ORDER_VVALUE] == 0 ? 'red' : 'green',
                        fontWeight: 'bold',
                        marginLeft: 15
                      },
                      children: [formatNumber(Number(item[ORDER_PPRICE]) * Number(item[ORDER_PNUMBER]) - Number(item[ORDER_VVALUE])), "\xA0VN\u0110"]
                    })]
                  }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                    children: ["Tr\u1EA1ng th\xE1i: ", status]
                  })]
                })]
              })
            }, item[ORDER_ID]);
          })
        })
      });
    }
  }]);

  return PagesHome;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (PagesHome);

/***/ }),

/***/ "./node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!./node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!./node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!./node_modules/sass-loader/dist/cjs.js!./resources/react/components/user/css/responsive.scss":
/*!******************************************************************************************************************************************************************************************************************************************************************************************************************************************!*\
  !*** ./node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!./node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!./node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!./node_modules/sass-loader/dist/cjs.js!./resources/react/components/user/css/responsive.scss ***!
  \******************************************************************************************************************************************************************************************************************************************************************************************************************************************/
/***/ ((module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var _node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../../../../../node_modules/css-loader/dist/runtime/api.js */ "./node_modules/css-loader/dist/runtime/api.js");
/* harmony import */ var _node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0__);
// Imports

var ___CSS_LOADER_EXPORT___ = _node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0___default()(function(i){return i[1]});
// Module
___CSS_LOADER_EXPORT___.push([module.id, "@media only screen and (min-width: 768px) {\n  #saleBanner .carousel-item {\n    width: 100%;\n    height: 300px;\n    font-size: 32px;\n    background-repeat: no-repeat;\n    background-size: cover;\n    background-position: center;\n  }\n\n  .product_type_item {\n    height: 150px;\n    width: 150px;\n  }\n\n  .product_type_item img {\n    width: 80%;\n  }\n\n  .user_menu {\n    height: 50px;\n  }\n\n  .main {\n    margin-bottom: 50px;\n  }\n\n  .product_list {\n    display: flex;\n    flex-wrap: wrap;\n  }\n\n  .product_list .product_item {\n    width: 50%;\n  }\n}\n@media only screen and (max-width: 768px) {\n  #saleBanner .carousel-item {\n    width: 100%;\n    height: 100px;\n    background-repeat: no-repeat;\n    background-size: cover;\n    background-position: center;\n  }\n\n  .carousel-indicators {\n    margin-bottom: 0px;\n    bottom: 5px;\n  }\n\n  .product_type_item {\n    height: 100px;\n    max-width: 150px;\n    min-width: 100px;\n    width: 33%;\n  }\n\n  .user_menu {\n    height: 40px;\n  }\n\n  .main {\n    margin-bottom: 40px;\n  }\n}\n.product_types_frame {\n  display: flex;\n  flex-wrap: wrap;\n  justify-content: space-between;\n  margin-top: 7px;\n}\n\n.product_type_item {\n  margin: 0px;\n  display: flex;\n  flex-direction: column;\n  align-items: unset;\n  text-align: center;\n  padding: 15px;\n}\n\n.product_type_item .product_type_image {\n  flex-grow: 1;\n  background-size: contain;\n  background-repeat: no-repeat;\n  background-position: center;\n  margin-bottom: 7px;\n  border-radius: 5px;\n}\n\n.product_type_item .product_type_title {\n  color: gray;\n  font-weight: bold;\n}\n\n.user_menu {\n  position: fixed;\n  left: 0px;\n  right: 0px;\n  z-index: 1;\n  bottom: 0;\n  background: #eee;\n  display: flex;\n  justify-content: space-around;\n}\n\n.user_menu .button {\n  flex-grow: 1;\n  margin: 0px;\n  justify-content: center;\n  border-left: solid thin #ccc;\n  position: relative;\n}\n\n.user_menu .button.active {\n  background: #FF9800;\n  color: white;\n  font-weight: bold;\n}\n\n.user_menu .button .quantity {\n  position: absolute;\n  right: 5px;\n  top: 5px;\n  padding: 0px 3px;\n  border-radius: 5px;\n  font-size: 10px;\n  border: solid thin white;\n  color: white;\n  text-align: center;\n  background: #FF5722;\n}\n\n.product_list .product_item {\n  padding: 5px;\n  color: gray;\n  position: relative;\n}\n\n.product_list .product_item .product_item_image {\n  width: 60px;\n  height: 60px;\n}\n\n.product_list .product_item .product_item_image img {\n  width: 100%;\n  height: 100%;\n  -o-object-fit: contain;\n     object-fit: contain;\n}\n\n.product_list .product_item .product_item_name {\n  font-size: medium;\n}\n\n.product_page .product_page_image_active {\n  width: 100%;\n  text-align: center;\n  height: 200px;\n  align-items: center;\n  padding: 10px;\n}\n\n.product_page .product_page_image_child {\n  width: 50px;\n  height: 50px;\n  margin: 5px;\n  padding: 2px;\n  margin-bottom: 15px;\n}\n\n.product_page .product_page_image_child.active {\n  border: solid thin orange;\n}\n\n.product_page .product_page_image_frame {\n  border-radius: 5px;\n  border: solid thin darkgray;\n}\n\n.product_page .product_page_image_frame .title {\n  padding: 5px 10px;\n  background: orange;\n  color: white;\n}\n\n.product_page .product_item_name {\n  font-size: medium;\n  color: orange;\n}\n\n.image {\n  width: unset !important;\n  height: unset !important;\n}", ""]);
// Exports
/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (___CSS_LOADER_EXPORT___);


/***/ }),

/***/ "./node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!./node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!./node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!./node_modules/sass-loader/dist/cjs.js!./resources/simulation/components/user/css/responsive.scss":
/*!***********************************************************************************************************************************************************************************************************************************************************************************************************************************************!*\
  !*** ./node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!./node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!./node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!./node_modules/sass-loader/dist/cjs.js!./resources/simulation/components/user/css/responsive.scss ***!
  \***********************************************************************************************************************************************************************************************************************************************************************************************************************************************/
/***/ ((module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var _node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../../../../../node_modules/css-loader/dist/runtime/api.js */ "./node_modules/css-loader/dist/runtime/api.js");
/* harmony import */ var _node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0__);
// Imports

var ___CSS_LOADER_EXPORT___ = _node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0___default()(function(i){return i[1]});
// Module
___CSS_LOADER_EXPORT___.push([module.id, "@media only screen and (min-width: 768px) {\n  #saleBanner .carousel-item {\n    width: 100%;\n    height: 300px;\n    font-size: 32px;\n    background-repeat: no-repeat;\n    background-size: cover;\n    background-position: center;\n  }\n\n  .product_type_item {\n    height: 150px;\n    width: 150px;\n  }\n\n  .product_type_item img {\n    width: 80%;\n  }\n\n  .user_menu {\n    height: 50px;\n  }\n\n  .main {\n    margin-bottom: 50px;\n  }\n\n  .product_list {\n    display: flex;\n    flex-wrap: wrap;\n  }\n\n  .product_list .product_item {\n    width: 50%;\n  }\n}\n@media only screen and (max-width: 768px) {\n  #saleBanner .carousel-item {\n    width: 100%;\n    height: 100px;\n    background-repeat: no-repeat;\n    background-size: cover;\n    background-position: center;\n  }\n\n  .carousel-indicators {\n    margin-bottom: 0px;\n    bottom: 5px;\n  }\n\n  .product_type_item {\n    height: 100px;\n    max-width: 150px;\n    min-width: 100px;\n    width: 33%;\n  }\n\n  .user_menu {\n    height: 40px;\n  }\n\n  .main {\n    margin-bottom: 40px;\n  }\n}\n.product_types_frame {\n  display: flex;\n  flex-wrap: wrap;\n  justify-content: space-between;\n  margin-top: 7px;\n}\n\n.product_type_item {\n  margin: 0px;\n  display: flex;\n  flex-direction: column;\n  align-items: unset;\n  text-align: center;\n  padding: 15px;\n}\n\n.product_type_item .product_type_image {\n  flex-grow: 1;\n  background-size: contain;\n  background-repeat: no-repeat;\n  background-position: center;\n  margin-bottom: 7px;\n  border-radius: 5px;\n}\n\n.product_type_item .product_type_title {\n  color: gray;\n  font-weight: bold;\n}\n\n.user_menu {\n  position: fixed;\n  left: 0px;\n  right: 0px;\n  z-index: 1;\n  bottom: 0;\n  background: #eee;\n  display: flex;\n  justify-content: space-around;\n}\n\n.user_menu .button {\n  flex-grow: 1;\n  margin: 0px;\n  justify-content: center;\n  border-left: solid thin #ccc;\n  position: relative;\n}\n\n.user_menu .button.active {\n  background: #FF9800;\n  color: white;\n  font-weight: bold;\n}\n\n.user_menu .button .quantity {\n  position: absolute;\n  right: 5px;\n  top: 5px;\n  padding: 0px 3px;\n  border-radius: 5px;\n  font-size: 10px;\n  border: solid thin white;\n  color: white;\n  text-align: center;\n  background: #FF5722;\n}\n\n.product_list .product_item {\n  padding: 5px;\n  color: gray;\n  position: relative;\n}\n\n.product_list .product_item .product_item_image {\n  width: 60px;\n  height: 60px;\n}\n\n.product_list .product_item .product_item_image img {\n  width: 100%;\n  height: 100%;\n  -o-object-fit: contain;\n     object-fit: contain;\n}\n\n.product_list .product_item .product_item_name {\n  font-size: medium;\n}\n\n.product_page .product_page_image_active {\n  width: 100%;\n  text-align: center;\n  height: 200px;\n  align-items: center;\n  padding: 10px;\n}\n\n.product_page .product_page_image_child {\n  width: 50px;\n  height: 50px;\n  margin: 5px;\n  padding: 2px;\n  margin-bottom: 15px;\n}\n\n.product_page .product_page_image_child.active {\n  border: solid thin orange;\n}\n\n.product_page .product_page_image_frame {\n  border-radius: 5px;\n  border: solid thin darkgray;\n}\n\n.product_page .product_page_image_frame .title {\n  padding: 5px 10px;\n  background: orange;\n  color: white;\n}\n\n.product_page .product_item_name {\n  font-size: medium;\n  color: orange;\n}\n\n.image {\n  width: unset !important;\n  height: unset !important;\n}", ""]);
// Exports
/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (___CSS_LOADER_EXPORT___);


/***/ }),

/***/ "./resources/react/components/user/css/responsive.scss":
/*!*************************************************************!*\
  !*** ./resources/react/components/user/css/responsive.scss ***!
  \*************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var _node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! !../../../../../node_modules/style-loader/dist/runtime/injectStylesIntoStyleTag.js */ "./node_modules/style-loader/dist/runtime/injectStylesIntoStyleTag.js");
/* harmony import */ var _node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _node_modules_css_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_1_node_modules_postcss_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_2_node_modules_sass_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_3_node_modules_sass_loader_dist_cjs_js_responsive_scss__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! !!../../../../../node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!../../../../../node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!../../../../../node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!../../../../../node_modules/sass-loader/dist/cjs.js!./responsive.scss */ "./node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!./node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!./node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!./node_modules/sass-loader/dist/cjs.js!./resources/react/components/user/css/responsive.scss");

            

var options = {};

options.insert = "head";
options.singleton = false;

var update = _node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0___default()(_node_modules_css_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_1_node_modules_postcss_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_2_node_modules_sass_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_3_node_modules_sass_loader_dist_cjs_js_responsive_scss__WEBPACK_IMPORTED_MODULE_1__.default, options);



/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (_node_modules_css_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_1_node_modules_postcss_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_2_node_modules_sass_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_3_node_modules_sass_loader_dist_cjs_js_responsive_scss__WEBPACK_IMPORTED_MODULE_1__.default.locals || {});

/***/ }),

/***/ "./resources/simulation/components/user/css/responsive.scss":
/*!******************************************************************!*\
  !*** ./resources/simulation/components/user/css/responsive.scss ***!
  \******************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var _node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! !../../../../../node_modules/style-loader/dist/runtime/injectStylesIntoStyleTag.js */ "./node_modules/style-loader/dist/runtime/injectStylesIntoStyleTag.js");
/* harmony import */ var _node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _node_modules_css_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_1_node_modules_postcss_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_2_node_modules_sass_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_3_node_modules_sass_loader_dist_cjs_js_responsive_scss__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! !!../../../../../node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!../../../../../node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!../../../../../node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!../../../../../node_modules/sass-loader/dist/cjs.js!./responsive.scss */ "./node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!./node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!./node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!./node_modules/sass-loader/dist/cjs.js!./resources/simulation/components/user/css/responsive.scss");

            

var options = {};

options.insert = "head";
options.singleton = false;

var update = _node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0___default()(_node_modules_css_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_1_node_modules_postcss_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_2_node_modules_sass_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_3_node_modules_sass_loader_dist_cjs_js_responsive_scss__WEBPACK_IMPORTED_MODULE_1__.default, options);



/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (_node_modules_css_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_1_node_modules_postcss_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_2_node_modules_sass_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_3_node_modules_sass_loader_dist_cjs_js_responsive_scss__WEBPACK_IMPORTED_MODULE_1__.default.locals || {});

/***/ })

}]);