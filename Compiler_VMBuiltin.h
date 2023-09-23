float sin(float rad);
float cos(float rad);
float tan(float rad);
float asin(float rad);
float acos(float rad);
float atan(float rad);
float sinh(float rad);
float cosh(float rad);
float tanh(float rad);
float asinh(float rad);
float acosh(float rad);
float atanh(float rad);

float sqrt(float val);
float exp(float val);

void print(char[] fmt);
int getADC(int port, int channel);
void setPin(int channel, int level);
void SDI12SingleMeasurement(int addr, float[] dst, int count);

void delay(int ms);
void waitNextMeasure();
void saveTable();