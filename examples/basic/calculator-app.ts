// Import the generated code directly from the index file instead of the calculator path
import { add, subtract, multiply, divide, Calculator } from './generated/calculator';

async function runCalculator() {
  console.log("Basic operations:");
  console.log(`5 + 3 = ${await add(5, 3)}`);
  console.log(`10 - 4 = ${await subtract(10, 4)}`);
  console.log(`6 * 7 = ${await multiply(6, 7)}`);
  console.log(`20 / 5 = ${await divide(20, 5)}`);

  console.log("\nUsing Calculator class:");
  const calculator = new Calculator();

  // Perform calculations
  console.log(`Calculator: 10 + 5 = ${await calculator.calculate(10, 5, "add")}`);
  console.log(`Calculator: 10 - 5 = ${await calculator.calculate(10, 5, "subtract")}`);
  console.log(`Calculator: 10 * 5 = ${await calculator.calculate(10, 5, "multiply")}`);
  console.log(`Calculator: 10 / 5 = ${await calculator.calculate(10, 5, "divide")}`);

  // Get history
  const history = await calculator.get_history();
  console.log("\nCalculation history:");
  history.forEach((entry, index) => {
    console.log(`${index + 1}. ${entry.a} ${entry.operation} ${entry.b} = ${entry.result}`);
  });

  // Clear history
  await calculator.clear_history();
  console.log("\nHistory cleared.");
  console.log(`History items: ${(await calculator.get_history()).length}`);
}

runCalculator().catch(console.error);